"""
Tests the three points where a character is copied into the archive.

A character holds what is genuinely irrecoverable — levels, skills,
progression — so unlike an account it cannot be reconstructed from the
XRPL mirror or anywhere else. The seams are:

- ``at_post_unpuppet``  the session's progress, banked as they go OOC
- chargen ``node_create``  the finished character, after chargen applies
- a genuine level-up  the one mid-session gain worth its own write

``archive_now()`` refuses on the router by default. A character is only
played on a shard, and the router sees a character session end every time
someone goes IC — archiving on those would put a write on the handoff
path for a copy no session could have changed. Chargen is the exception
and says so explicitly.

evennia test --settings settings tests.typeclass_tests.test_character_archive_seams
"""

from unittest.mock import patch

from evennia.utils.test_resources import BaseEvenniaTest
from evennia_archive.mixins import ARCHIVE_ID_KEY
from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, ROLE_SHARD
from twisted.internet import defer

import typeclasses.actors.character as character_module


def _sync_defer(func, *args, **kwargs):
    """Run *func* synchronously and return an already-fired Deferred."""
    d = defer.Deferred()
    try:
        result = func(*args, **kwargs)
        d.callback(result)
    except Exception as e:
        d.errback(e)
    return d


class CharacterArchiveTestBase(BaseEvenniaTest):
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def _archive_calls(self, role, **kwargs):
        with patch.object(
            character_module.threads, "deferToThread", _sync_defer
        ), patch("evennia_shards.get_role", return_value=role), patch(
            "evennia_archive.api.archive"
        ) as archive:
            self.char1.archive_now(**kwargs)
        return archive


class TestArchiveNowRoleGuard(CharacterArchiveTestBase):
    """Where a character archive is allowed to happen."""

    def test_shard_archives(self):
        self._archive_calls(ROLE_SHARD).assert_called_once_with(self.char1)

    def test_monolith_archives(self):
        self._archive_calls(ROLE_MONOLITH).assert_called_once_with(self.char1)

    def test_router_does_not_archive(self):
        """Going IC ends a router session; that must not trigger a write."""
        self._archive_calls(ROLE_ROUTER).assert_not_called()

    def test_router_archives_when_explicitly_allowed(self):
        """Chargen's exception — it has nowhere else to run."""
        self._archive_calls(
            ROLE_ROUTER, allow_router=True
        ).assert_called_once_with(self.char1)

    def test_failure_is_logged_not_raised(self):
        with patch.object(
            character_module.threads, "deferToThread", _sync_defer
        ), patch("evennia_shards.get_role", return_value=ROLE_SHARD), patch(
            "evennia_archive.api.archive",
            side_effect=RuntimeError("archive is down"),
        ), patch.object(character_module.logger, "log_err") as log_err:
            self.char1.archive_now()

        log_err.assert_called_once()

    def test_undeferred_failure_is_also_logged(self):
        with patch(
            "evennia_shards.get_role", return_value=ROLE_SHARD
        ), patch(
            "evennia_archive.api.archive",
            side_effect=RuntimeError("archive is down"),
        ), patch.object(
            character_module.logger, "log_err"
        ) as log_err, patch.object(
            character_module.logger, "log_trace"
        ):
            self.char1.archive_now(defer=False)

        log_err.assert_called_once()


class TestUnpuppetArchives(CharacterArchiveTestBase):
    """Going OOC banks the session's progress."""

    def test_at_post_unpuppet_archives(self):
        with patch.object(
            type(self.char1), "archive_now"
        ) as archive_now, patch(
            "blockchain.xrpl.services.telemetry.TelemetryService."
            "record_session_end"
        ):
            self.char1.at_post_unpuppet(self.account)

        archive_now.assert_called_once()

    def test_link_dead_unpuppet_still_archives(self):
        """The sweep passes account=None; the archive must happen anyway."""
        with patch.object(
            type(self.char1), "archive_now"
        ) as archive_now, patch(
            "blockchain.xrpl.services.telemetry.TelemetryService."
            "record_session_end"
        ):
            self.char1.at_post_unpuppet(None)

        archive_now.assert_called_once()


class TestLevelUpArchives(CharacterArchiveTestBase):
    """A level is the one mid-session gain worth its own write."""

    def test_level_up_archives(self):
        from utils.experience_table import get_xp_for_next_level

        self.char1.experience_points = 0
        self.char1.highest_xp_level_earned = self.char1.total_level
        needed = get_xp_for_next_level(self.char1.total_level)

        with patch.object(type(self.char1), "archive_now") as archive_now:
            self.char1.at_gain_experience_points(needed)

        self.assertTrue(
            archive_now.called,
            "Levelling up did not archive the character.",
        )

    def test_xp_short_of_a_level_does_not_archive(self):
        """Every XP gain archiving would be a write per kill."""
        from utils.experience_table import get_xp_for_next_level

        self.char1.experience_points = 0
        self.char1.highest_xp_level_earned = self.char1.total_level
        needed = get_xp_for_next_level(self.char1.total_level)

        with patch.object(type(self.char1), "archive_now") as archive_now:
            self.char1.at_gain_experience_points(max(needed - 1, 0))

        archive_now.assert_not_called()


class TestGuildLevelArchives(CharacterArchiveTestBase):
    """Spending a pending level on a class is irreversible."""

    def _class_instance(self):
        """The warrior class, imported by name.

        Character classes are module-level *instances* of CharClassBase,
        not subclasses, so discovering one via __subclasses__ finds
        nothing — and turns these tests into skips that read as passes.
        """
        from typeclasses.actors.char_classes.warrior import WARRIOR

        return WARRIOR

    def test_spending_a_level_archives(self):
        char_class = self._class_instance()
        self.char1.db.classes = {
            char_class.key: {"level": 1, "skill_pts_available": 0}
        }
        self.char1.levels_to_spend = 1

        with patch.object(type(self.char1), "archive_now") as archive_now:
            char_class.at_gain_subsequent_level_in_class(self.char1)

        archive_now.assert_called_once()

    def test_refused_advance_does_not_archive(self):
        """No levels to spend means nothing changed, so nothing to bank."""
        char_class = self._class_instance()
        self.char1.db.classes = {
            char_class.key: {"level": 1, "skill_pts_available": 0}
        }
        self.char1.levels_to_spend = 0

        with patch.object(type(self.char1), "archive_now") as archive_now:
            char_class.at_gain_subsequent_level_in_class(self.char1)

        archive_now.assert_not_called()


class TestDeleteRemovesTheArchivedCopy(CharacterArchiveTestBase):
    """chardelete means gone.

    Without this the character returns at the next world rebuild, over
    the account's cap and holding a name that may since have been
    reissued to somebody else.
    """

    def test_allowed_delete_removes_the_archived_copy(self):
        self.char1.account_wallet = "rDeleteTestWallet"

        with patch("evennia_archive.api.delete") as delete:
            self.assertTrue(self.char1.at_object_delete())

        delete.assert_called_once_with(self.char1.archive_id)

    def test_refused_delete_leaves_the_archive_alone(self):
        """A character that still owns something is not deleted at all."""
        with patch.object(
            type(self.char1), "get_gold", return_value=5
        ), patch("evennia_archive.api.delete") as delete:
            self.assertFalse(self.char1.at_object_delete())

        delete.assert_not_called()

    def test_unarchived_character_does_not_call_delete(self):
        """Nothing to remove, and delete() takes an identifier."""
        self.char1.attributes.remove(ARCHIVE_ID_KEY)

        with patch("evennia_archive.api.delete") as delete:
            self.assertTrue(self.char1.at_object_delete())

        delete.assert_not_called()

    def test_failure_does_not_block_the_delete(self):
        """The player asked to delete; the archive is not their problem."""
        with patch(
            "evennia_archive.api.delete",
            side_effect=RuntimeError("archive is down"),
        ), patch.object(character_module.logger, "log_err"), patch.object(
            character_module.logger, "log_trace"
        ), patch(
            "blockchain.xrpl.services.reconciliation.record_failure"
        ):
            self.assertTrue(self.char1.at_object_delete())

    def test_failure_is_recorded_for_an_admin(self):
        """A surviving copy needs a person, so it goes on the failures list."""
        self.char1.account_wallet = "rDeleteTestWallet"

        with patch(
            "evennia_archive.api.delete",
            side_effect=RuntimeError("archive is down"),
        ), patch.object(character_module.logger, "log_err"), patch.object(
            character_module.logger, "log_trace"
        ), patch(
            "blockchain.xrpl.services.reconciliation.record_failure"
        ) as record:
            self.char1.at_object_delete()

        record.assert_called_once()
        kwargs = record.call_args.kwargs
        self.assertEqual(kwargs["operation"], "archive_delete_character")
        self.assertEqual(kwargs["wallet_address"], "rDeleteTestWallet")
        self.assertEqual(kwargs["character_key"], self.char1.key)


class TestAccountWalletStamp(CharacterArchiveTestBase):
    """The only thing tying a restored character back to an account."""

    def test_unstamped_character_reads_none(self):
        self.assertIsNone(self.char1.account_wallet)

    def test_stamp_is_stored_unpickled(self):
        """Plain string equality is the whole point of the copy."""
        self.char1.account_wallet = "rWalletStampTest"

        attr = self.char1.attributes.get(
            "account_wallet", return_obj=True, strattr=True
        )
        self.assertEqual(attr.db_strvalue, "rWalletStampTest")
        self.assertIsNone(attr.db_value)

    def test_stamp_round_trips(self):
        self.char1.account_wallet = "rWalletStampTest"
        self.assertEqual(self.char1.account_wallet, "rWalletStampTest")

    def test_clearing_removes_the_attribute(self):
        self.char1.account_wallet = "rWalletStampTest"
        self.char1.account_wallet = None
        self.assertIsNone(self.char1.account_wallet)

    def test_stamp_survives_without_an_account(self):
        """After a restore, self.account is exactly what is missing."""
        self.char1.account_wallet = "rWalletStampTest"
        self.char1.db_account = None
        self.char1.save()

        self.assertEqual(self.char1.account_wallet, "rWalletStampTest")

    def test_archive_search_finds_it_by_wallet(self):
        """The lookup the restore path will actually run."""
        from evennia_archive.api import archive, find

        self.char1.account_wallet = "rWalletFindTest"
        self.char1.at_archive_init()
        archive(self.char1)

        found = find("account_wallet", "rWalletFindTest", model="objectdb")

        self.assertIn(self.char1.archive_id, found)


class TestChargenRefusesArchivedNames(CharacterArchiveTestBase):
    """A name held by an archived character is not available.

    After a world rebuild the live database has no characters in it, so
    every name looks free until its owner signs in. Handing one out in
    that window would either cost the returning player their name, or
    force a rename that detaches them from gold and items — both keyed on
    the character's name in the XRPL mirror.
    """

    def _check(self, name):
        from server.main_menu.chargen import chargen_menu

        self.account.ndb._chargen = {"session": None}
        # _handle_name_input is the goto handler that validates; node_name
        # only renders the prompt. It returns a bare node name on success
        # and a (node, {"error": ...}) tuple on refusal, so normalise.
        result = chargen_menu._handle_name_input(self.account, name)
        return result if isinstance(result, tuple) else (result, {})

    def test_a_free_name_is_accepted(self):
        result = self._check("Unusedname")
        self.assertEqual(result[0], "node_confirm")

    def test_a_live_name_is_refused(self):
        result = self._check(self.char1.key)
        self.assertEqual(result[0], "node_name")
        self.assertIn("already taken", result[1]["error"])

    def test_an_archived_name_is_refused(self):
        """The case that only exists after a rebuild."""
        from evennia_archive.api import archive

        self.char1.at_archive_init()
        archive(self.char1)
        archived_name = self.char1.key

        # Simulate the rebuild: the character is gone from the live world
        # but its archived copy remains. _delete_archived_copy is
        # suppressed because a world rebuild destroys the database — it
        # does not run chardelete, which would take the archive with it.
        with patch.object(type(self.char1), "_delete_archived_copy"):
            self.char1.delete()

        result = self._check(archived_name)

        self.assertEqual(result[0], "node_name")
        self.assertIn("already taken", result[1]["error"])


class TestChargenStampsTheWallet(CharacterArchiveTestBase):
    """Chargen must stamp before it archives, or the copy is unfindable."""

    def test_wallet_is_stamped_before_the_archive(self):
        from server.main_menu.chargen import chargen_menu

        self.account.wallet_address = "rChargenStampTest"
        self.account.ndb._chargen = {
            "session": None,
            "is_remort": False,
            "char_name": "Stampy",
        }

        seen = {}

        def _record(*args, **kwargs):
            seen["wallet"] = self.char1.account_wallet

        with patch.object(
            self.account, "create_character",
            return_value=(self.char1, None),
        ), patch.object(
            chargen_menu, "_apply_chargen_to_character"
        ), patch.object(
            type(self.char1), "archive_now", side_effect=_record
        ):
            chargen_menu.node_create(self.account, "")

        self.assertEqual(
            seen.get("wallet"),
            "rChargenStampTest",
            "The character was archived before its wallet was stamped, "
            "so the archived copy cannot be found by wallet.",
        )


class TestRemortArchives(CharacterArchiveTestBase):
    """A remort rebuilds the character wholesale.

    The remort flow is not yet play-tested and may well be refactored.
    This test is here so that a refactor has to decide about the archive
    call deliberately rather than drop it by accident.
    """

    def test_remort_archives_the_character(self):
        from server.main_menu.chargen import chargen_menu

        self.account.ndb._chargen = {
            "session": None,
            "is_remort": True,
            "character": self.char1,
            "num_remorts": 1,
        }

        with patch.object(
            type(self.char1), "archive_now"
        ) as archive_now, patch.object(
            chargen_menu, "_apply_chargen_to_character"
        ):
            chargen_menu.node_create(self.account, "")

        archive_now.assert_called_once()


class TestTrainingArchives(CharacterArchiveTestBase):
    """A mastery tier costs points that cannot be refunded."""

    def _trainer(self):
        trainer = type("_Trainer", (), {})()
        trainer.key = "a trainer"
        trainer.trainer_class = None
        return trainer

    def test_general_skill_training_archives(self):
        from commands.npc_cmds import cmdset_trainer

        self.char1.general_skill_pts_available = 5
        self.char1.db.general_skill_mastery_levels = {}

        with patch.object(
            type(self.char1), "archive_now"
        ) as archive_now, patch.object(
            cmdset_trainer, "reconcile_grants", return_value={}
        ), patch.object(
            cmdset_trainer, "format_gains", return_value=[]
        ):
            cmdset_trainer._resolve_skill_training(
                self.char1, self._trainer(), "stealth",
                is_general=True, current=0, target=1, pts_cost=1,
            )

        archive_now.assert_called_once()

    def test_weapon_training_archives(self):
        from commands.npc_cmds import cmdset_trainer

        self.char1.weapon_skill_pts_available = 5
        self.char1.db.weapon_skill_mastery_levels = {}

        with patch.object(type(self.char1), "archive_now") as archive_now:
            cmdset_trainer._resolve_weapon_training(
                self.char1, self._trainer(), "battleaxe",
                current=0, target=1, pts_cost=1,
            )

        archive_now.assert_called_once()

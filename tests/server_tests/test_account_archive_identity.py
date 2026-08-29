"""
Tests that accounts and characters carry an archive identity.

``archive_id`` is what lets a row in the live database and a row in the
archive be known to be the same object, since primary keys are re-issued
by the world rebuild the archive exists to survive. It is minted once at
creation and never changes.

Both typeclasses carry ``ArchivableMixin``, but only the character gets
its mint for free: ``Account.at_account_creation`` overrides the hook
without calling ``super()``, so the account mints explicitly. That is the
line these tests protect — removing it fails nothing at runtime and
leaves every account unarchivable.

evennia test --settings settings tests.server_tests.test_account_archive_identity
"""

import uuid
from unittest.mock import patch

from evennia.utils.test_resources import BaseEvenniaTest
from evennia_archive.mixins import ARCHIVE_ID_KEY
from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, ROLE_SHARD
from twisted.internet import defer

import typeclasses.accounts.accounts as accounts_module


def _sync_defer(func, *args, **kwargs):
    """Run *func* synchronously and return an already-fired Deferred."""
    d = defer.Deferred()
    try:
        result = func(*args, **kwargs)
        d.callback(result)
    except Exception as e:
        d.errback(e)
    return d


class TestAccountArchiveIdentity(BaseEvenniaTest):
    """Accounts mint an archive_id despite the overridden creation hook."""

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def test_account_creation_mints_an_archive_id(self):
        self.account.attributes.remove(ARCHIVE_ID_KEY)
        self.account.at_account_creation()

        self.assertIsNotNone(
            self.account.archive_id,
            "at_account_creation did not mint an archive_id. It overrides "
            "the hook without calling super(), so ArchivableMixin never "
            "runs — the explicit at_archive_init() call is what mints it.",
        )

    def test_minted_value_is_a_canonical_uuid(self):
        """String equality is case-sensitive where uuid comparison is not."""
        self.account.attributes.remove(ARCHIVE_ID_KEY)
        self.account.at_account_creation()

        minted = self.account.archive_id
        self.assertEqual(str(uuid.UUID(minted)), minted)

    def test_archive_id_is_stored_unpickled(self):
        """It has to be queryable as a plain string, not as pickled bytes."""
        self.account.attributes.remove(ARCHIVE_ID_KEY)
        self.account.at_account_creation()

        attr = self.account.attributes.get(
            ARCHIVE_ID_KEY, return_obj=True, strattr=True
        )
        self.assertIsNotNone(attr.db_strvalue)
        self.assertIsNone(attr.db_value)

    def test_identity_is_never_reminted(self):
        """Reminting would strand whatever is already archived under it."""
        self.account.attributes.remove(ARCHIVE_ID_KEY)
        self.account.at_account_creation()
        first = self.account.archive_id

        self.account.at_account_creation()

        self.assertEqual(self.account.archive_id, first)


class TestArchiveNowIsScopedToTheRouter(BaseEvenniaTest):
    """archive_now() writes on the router and monolith, never on a shard.

    A shard sees a session end on every IC/OOC handoff. Archiving there
    would put a write on the hot path to copy state the router already
    holds — accounts only change while the player is out of character.
    """

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def _archive_calls(self, role):
        with patch(
            "typeclasses.accounts.accounts.defer_to_db_thread", _sync_defer
        ), patch("evennia_shards.get_role", return_value=role), patch(
            "evennia_archive.api.archive"
        ) as archive:
            self.account.archive_now()
        return archive

    def test_monolith_archives(self):
        self._archive_calls(ROLE_MONOLITH).assert_called_once_with(
            self.account
        )

    def test_router_archives(self):
        self._archive_calls(ROLE_ROUTER).assert_called_once_with(self.account)

    def test_shard_does_not_archive(self):
        self._archive_calls(ROLE_SHARD).assert_not_called()

    def test_failure_is_logged_not_raised(self):
        """A failed archive must never reach the player."""
        with patch(
            "typeclasses.accounts.accounts.defer_to_db_thread", _sync_defer
        ), patch("evennia_shards.get_role", return_value=ROLE_MONOLITH), patch(
            "evennia_archive.api.archive",
            side_effect=RuntimeError("archive is down"),
        ), patch.object(accounts_module.logger, "log_err") as log_err:
            self.account.archive_now()

        log_err.assert_called_once()

    def test_undeferred_failure_is_also_logged(self):
        """The shutdown path runs inline, so it needs its own guard."""
        with patch(
            "evennia_shards.get_role", return_value=ROLE_MONOLITH
        ), patch(
            "evennia_archive.api.archive",
            side_effect=RuntimeError("archive is down"),
        ), patch.object(
            accounts_module.logger, "log_err"
        ) as log_err, patch.object(
            accounts_module.logger, "log_trace"
        ):
            self.account.archive_now(defer=False)

        log_err.assert_called_once()


class TestDisconnectRefreshesTheArchive(BaseEvenniaTest):
    """The freshness seam: every session end rewrites the copy."""

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def test_at_disconnect_archives(self):
        with patch.object(
            type(self.account), "archive_now"
        ) as archive_now:
            self.account.at_disconnect(reason="quit")

        archive_now.assert_called_once()

    def test_at_disconnect_defers(self):
        """The reactor is healthy here, so nobody should wait on the write."""
        with patch.object(
            type(self.account), "archive_now"
        ) as archive_now:
            self.account.at_disconnect(reason="quit")

        _, kwargs = archive_now.call_args
        self.assertNotEqual(
            kwargs.get("defer"),
            False,
            "at_disconnect archived synchronously; the player waits for it.",
        )


class TestCharacterArchiveIdentity(BaseEvenniaTest):
    """Characters mint theirs through the mixin, via super()."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def test_character_has_an_archive_id(self):
        self.assertIsNotNone(
            self.char1.archive_id,
            "FCMCharacter.at_object_creation calls super() and "
            "ArchivableMixin is first in the MRO, so the mint should "
            "happen without an explicit call.",
        )

    def test_character_identity_is_never_reminted(self):
        first = self.char1.archive_id
        self.char1.at_archive_init()
        self.assertEqual(self.char1.archive_id, first)

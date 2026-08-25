"""
Tests the archive branch of wallet sign-in.

Once the wallet is verified, the connect flow asks three questions in
order: is there a live account for this wallet, is there an archived one,
and only then does it create a new one. Getting that order wrong is not a
cosmetic bug — creating an account first takes the username and mints a
fresh archive identity, which leaves the archived account unrestorable.

The Xaman polling is not exercised here. Everything the archive branch
does lives in module-level functions taking a session, so they are called
directly; ``deferToThread`` is patched to run inline so each assertion
lands in the same call.

evennia test --settings settings tests.server_tests.test_connect_archive_restore
"""

from unittest.mock import MagicMock, patch

from django.conf import settings

from evennia.utils.test_resources import BaseEvenniaTest
from twisted.internet import defer
from twisted.python.failure import Failure

import commands.unloggedin_cmds.cmd_override_unconnected_connect as connect


WALLET = "rConnectArchiveRestoreTestWallet"
ADDRESS = "127.0.0.1"


def _sync_defer(func, *args, **kwargs):
    """Run *func* synchronously and return an already-fired Deferred."""
    d = defer.Deferred()
    try:
        result = func(*args, **kwargs)
        d.callback(result)
    except Exception as e:
        d.errback(e)
    return d


class _Ndb:
    """Stand-in for session.ndb — arbitrary attributes, no persistence."""

    def __getattr__(self, name):
        return None


class FakeSession:
    """The smallest session the archive branch actually touches.

    It reads nothing back off the session; it writes messages, stashes
    the wallet on ndb for the username callback, and hands the account to
    the session handler. Recording those three is enough.
    """

    def __init__(self):
        self.messages = []
        self.ndb = _Ndb()
        self.address = ADDRESS
        self.logged_in_as = None
        self.sessionhandler = self

    def msg(self, text=None, **kwargs):
        self.messages.append(str(text))

    def login(self, session, account):
        self.logged_in_as = account

    @property
    def output(self):
        return "\n".join(self.messages)


@patch.object(connect.threads, "deferToThread", _sync_defer)
class TestArchiveLookupBranch(BaseEvenniaTest):
    """Which path a wallet takes when no live account exists."""

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.fake_session = FakeSession()

    def test_no_archived_account_goes_to_creation(self):
        """A miss must hand off to registration, not stall."""
        with patch.object(connect, "_begin_account_creation") as begin:
            connect._on_archive_lookup(self.fake_session, ADDRESS, WALLET, [])

        begin.assert_called_once_with(self.fake_session, ADDRESS, WALLET)
        self.assertIn("No archived account found", self.fake_session.output)

    def test_archived_account_is_restored_and_logged_in(self):
        """A hit restores the identity and logs that account in."""
        restored = self.account

        with patch.object(
            connect, "_restore_account", return_value=restored
        ) as restore, patch.object(
            connect, "_restore_characters", return_value=[]
        ), patch.object(connect, "_login_account") as login:
            connect._on_archive_lookup(
                self.fake_session, ADDRESS, WALLET, ["some-archive-id"]
            )

        restore.assert_called_once_with("some-archive-id")
        login.assert_called_once_with(self.fake_session, ADDRESS, restored)
        self.assertIn("restoring your account", self.fake_session.output)

    def test_a_hit_never_reaches_account_creation(self):
        """Creating alongside a restore would give the player two accounts."""
        with patch.object(
            connect, "_restore_account", return_value=self.account
        ), patch.object(
            connect, "_restore_characters", return_value=[]
        ), patch.object(connect, "_login_account"), patch.object(
            connect, "_begin_account_creation"
        ) as begin:
            connect._on_archive_lookup(
                self.fake_session, ADDRESS, WALLET, ["some-archive-id"]
            )

        begin.assert_not_called()

    def test_several_hits_takes_the_first_and_logs(self):
        """A wallet identifies one account; more than one is a defect.

        The player is not blocked by it — they get an account back — but
        it must be visible in the log rather than silently resolved.
        """
        with patch.object(
            connect, "_restore_account", return_value=self.account
        ) as restore, patch.object(
            connect, "_restore_characters", return_value=[]
        ), patch.object(
            connect, "_login_account"
        ), patch.object(connect.logger, "log_err") as log_err:
            connect._on_archive_lookup(
                self.fake_session, ADDRESS, WALLET, ["first-id", "second-id"]
            )

        restore.assert_called_once_with("first-id")
        log_err.assert_called_once()


@patch.object(connect.threads, "deferToThread", _sync_defer)
class TestArchiveUnreachableRefuses(BaseEvenniaTest):
    """A failed archive lookup must refuse, never fall through.

    This is the one behaviour with no other guard. If the archive cannot
    be read and the flow creates an account anyway, that account takes
    the username and mints its own archive identity — and the player's
    real account becomes permanently unrestorable. A momentary fault
    would cause irreversible damage, so the flow stops and asks them to
    retry.
    """

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.fake_session = FakeSession()
        # Built directly rather than via defer.fail(), which leaves an
        # unconsumed Deferred and logs "Unhandled error in Deferred".
        self.failure = Failure(RuntimeError("archive is unreachable"))
        self.failure.cleanFailure()

    def test_error_does_not_create_an_account(self):
        with patch.object(connect, "_begin_account_creation") as begin:
            connect._on_archive_error(self.fake_session, self.failure)

        begin.assert_not_called()

    def test_error_tells_the_player_to_retry(self):
        with patch.object(connect.logger, "log_err"):
            connect._on_archive_error(self.fake_session, self.failure)

        self.assertIn("Please try again shortly", self.fake_session.output)

    def test_error_is_logged(self):
        with patch.object(connect.logger, "log_err") as log_err:
            connect._on_archive_error(self.fake_session, self.failure)

        log_err.assert_called_once()

    def test_error_does_not_log_the_player_in(self):
        with patch.object(connect.logger, "log_err"):
            connect._on_archive_error(self.fake_session, self.failure)

        self.assertIsNone(self.fake_session.logged_in_as)


@patch.object(connect.threads, "deferToThread", _sync_defer)
class TestBankRecovery(BaseEvenniaTest):
    """Banked items are rebuilt from the mirror, which is only ever read."""

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.fake_session = FakeSession()
        self.account.wallet_address = WALLET

    def test_banked_items_are_searched_by_wallet_alone(self):
        """No character_key involved, so no name questions apply here."""
        with patch(
            "blockchain.xrpl.services.nft.NFTService.get_account_nfts",
            return_value=[],
        ) as get:
            connect._restore_bank(self.account)

        get.assert_called_once_with(WALLET)

    def test_no_wallet_recovers_nothing(self):
        self.account.attributes.remove("wallet_address")

        with patch(
            "blockchain.xrpl.services.nft.NFTService.get_account_nfts"
        ) as get:
            self.assertEqual(connect._restore_bank(self.account), 0)

        get.assert_not_called()

    def test_each_row_is_rebuilt_as_a_recovery(self):
        """Without recovering=True the mirror books a fresh deposit."""
        row = type("_Row", (), {"nftoken_id": "TOKENA"})()

        with patch(
            "blockchain.xrpl.services.nft.NFTService.get_account_nfts",
            return_value=[row],
        ), patch(
            "commands.room_specific_cmds.bank.cmd_balance.ensure_bank",
            return_value=self.obj1,
        ), patch(
            "typeclasses.items.base_nft_item.BaseNFTItem.spawn_into"
        ) as spawn:
            count = connect._restore_bank(self.account)

        spawn.assert_called_once_with("TOKENA", self.obj1, recovering=True)
        self.assertEqual(count, 1)

    def test_rebuilt_items_are_not_left_resident(self):
        """Recovery runs on the router, which must not hold game objects."""
        row = type("_Row", (), {"nftoken_id": "TOKENA"})()

        with patch(
            "blockchain.xrpl.services.nft.NFTService.get_account_nfts",
            return_value=[row],
        ), patch(
            "commands.room_specific_cmds.bank.cmd_balance.ensure_bank",
            return_value=self.obj1,
        ), patch(
            "typeclasses.items.base_nft_item.BaseNFTItem.spawn_into"
        ) as spawn:
            connect._restore_bank(self.account)

        spawn.return_value.flush_from_cache.assert_called_once_with(force=True)

    def test_an_unrebuildable_row_does_not_stop_the_rest(self):
        rows = [
            type("_Row", (), {"nftoken_id": "TOKENA"})(),
            type("_Row", (), {"nftoken_id": "TOKENB"})(),
        ]

        with patch(
            "blockchain.xrpl.services.nft.NFTService.get_account_nfts",
            return_value=rows,
        ), patch(
            "commands.room_specific_cmds.bank.cmd_balance.ensure_bank",
            return_value=self.obj1,
        ), patch(
            "typeclasses.items.base_nft_item.BaseNFTItem.spawn_into",
            side_effect=[None, MagicMock()],
        ), patch.object(connect.logger, "log_err"):
            count = connect._restore_bank(self.account)

        self.assertEqual(count, 1)

    def _balances(self, rows):
        """Run the balance restore against a stubbed mirror."""
        bank = self.obj1
        with patch(
            "blockchain.xrpl.services.fungible.FungibleService"
            ".get_all_balances",
            return_value=rows,
        ), patch.object(connect.logger, "log_err"):
            from blockchain.xrpl.models import FungibleGameState
            connect._restore_balances(
                bank, WALLET, FungibleGameState.LOCATION_ACCOUNT
            )
        return bank

    @staticmethod
    def _row(currency_code, balance):
        return type(
            "_Row", (), {"currency_code": currency_code, "balance": balance}
        )()

    def test_gold_is_written_to_the_bank(self):
        bank = self._balances([self._row(settings.XRPL_GOLD_CURRENCY_CODE, 500)])

        self.assertEqual(bank.db.gold, 500)

    def test_resources_are_written_by_resource_id(self):
        with patch(
            "blockchain.xrpl.currency_cache.get_resource_id", return_value=3
        ):
            bank = self._balances([self._row("FCMFlour", 9)])

        self.assertEqual(bank.db.resources, {3: 9})

    def test_a_proxy_token_is_never_credited(self):
        """P-tokens price NFTs against an AMM; they are not player currency."""
        with patch(
            "blockchain.xrpl.currency_cache.get_resource_id", return_value=None
        ):
            bank = self._balances([self._row("PGold", 1000)])

        self.assertEqual(bank.db.gold, 0)
        self.assertEqual(bank.db.resources, {})

    def test_the_mirror_is_never_written(self):
        """Going through the mixin would re-bank gold that is already banked."""
        from blockchain.xrpl.services.fungible import FungibleService

        with patch.object(FungibleService, "bank") as bank_call, patch.object(
            FungibleService, "deposit_from_chain"
        ) as deposit:
            self._balances([self._row(settings.XRPL_GOLD_CURRENCY_CODE, 500)])

        bank_call.assert_not_called()
        deposit.assert_not_called()

    def test_banked_items_are_stamped_global(self):
        """The insert runs on the router, in a worker thread, with no
        tenant context — unstamped rows are refused by the shards guard.

        "*" matches the bank itself, so a banked item is reachable from
        whichever shard the account is playing on.
        """
        row = type("_Row", (), {"nftoken_id": "TOKENA"})()

        with patch.object(
            connect, "_global_shard", return_value="*"
        ), patch.object(connect, "_stamping_as") as stamping, patch(
            "typeclasses.items.base_nft_item.BaseNFTItem.spawn_into"
        ), patch(
            "blockchain.xrpl.services.nft.NFTService.get_account_nfts",
            return_value=[row],
        ), patch(
            "commands.room_specific_cmds.bank.cmd_balance.ensure_bank",
            return_value=self.obj1,
        ), patch.object(connect, "_restore_balances"):
            connect._restore_bank(self.account)

        stamping.assert_called_once_with("*")

    def test_monolith_stamps_nothing(self):
        """No shard_id column exists there, so entering a context would
        fail rather than help."""
        from evennia_shards import ROLE_MONOLITH

        with patch("evennia_shards.get_role", return_value=ROLE_MONOLITH):
            self.assertIsNone(connect._global_shard())
            self.assertIsNone(connect._recovery_shard(self.obj1))

    def test_a_failed_bank_recovery_still_reaches_the_characters(self):
        """A bank fault must not cost them their characters as well."""
        failure = Failure(RuntimeError("mirror unreachable"))
        failure.cleanFailure()

        with patch.object(
            connect, "_restore_characters", return_value=[]
        ) as restore_chars, patch.object(
            connect, "_login_account"
        ), patch.object(connect.logger, "log_err"):
            connect._on_bank_restore_error(
                self.fake_session, ADDRESS, self.account, failure
            )

        restore_chars.assert_called_once()
        self.assertIn("ownership records are intact", self.fake_session.output)


@patch.object(connect.threads, "deferToThread", _sync_defer)
class TestCharacterRecovery(BaseEvenniaTest):
    """Restoring an account is only half the job.

    A restored character comes back with db_account dropped, so it exists
    and cannot be played until both links are put back — the foreign key
    the character side reads, and the account-side list `ic` is driven
    from.
    """

    account_typeclass = "typeclasses.accounts.accounts.Account"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.fake_session = FakeSession()
        self.account.wallet_address = WALLET

    def test_characters_are_searched_by_the_stamped_wallet(self):
        with patch("evennia_archive.api.find", return_value=[]) as find:
            connect._restore_characters(self.account)

        find.assert_called_once_with(
            "account_wallet", WALLET, model="objectdb"
        )

    def test_no_wallet_searches_nothing(self):
        """A walletless account has no key to search on."""
        self.account.wallet_address = None

        with patch("evennia_archive.api.find") as find:
            result = connect._restore_characters(self.account)

        find.assert_not_called()
        self.assertEqual(result, [])

    def test_restored_character_is_reattached_both_ways(self):
        """One link alone leaves a character that exists and cannot be played."""
        self.char1.db_account = None
        self.char1.save(update_fields=["db_account"])

        connect._reattach_character(self.account, self.char1)

        self.assertEqual(self.char1.db_account, self.account)
        self.assertIn(self.char1, self.account.characters.all())

    def test_recovery_reports_what_it_found(self):
        with patch.object(connect, "_login_account"), patch.object(
            connect, "_reattach_character"
        ):
            connect._on_characters_restored(
                self.fake_session, ADDRESS, self.account, [self.char1]
            )

        self.assertIn("Recovered 1 character", self.fake_session.output)
        self.assertIn(str(self.char1.key), self.fake_session.output)

    def test_no_characters_is_said_plainly(self):
        with patch.object(connect, "_login_account"):
            connect._on_characters_restored(
                self.fake_session, ADDRESS, self.account, []
            )

        self.assertIn("No archived characters found", self.fake_session.output)

    def test_login_happens_even_with_no_characters(self):
        with patch.object(connect, "_login_account") as login:
            connect._on_characters_restored(
                self.fake_session, ADDRESS, self.account, []
            )

        login.assert_called_once()

    def test_a_failed_character_search_still_logs_them_in(self):
        """The account is live and usable; blocking sign-in costs more."""
        failure = Failure(RuntimeError("archive is unreachable"))
        failure.cleanFailure()

        with patch.object(connect, "_login_account") as login, patch.object(
            connect.logger, "log_err"
        ):
            connect._on_character_restore_error(
                self.fake_session, ADDRESS, self.account, failure
            )

        login.assert_called_once()
        self.assertIn("still archived", self.fake_session.output)

    def test_character_assets_are_filtered_by_name(self):
        """Items are keyed on the character, not just the wallet."""
        with patch(
            "blockchain.xrpl.services.nft.NFTService.get_character_nfts",
            return_value=[],
        ) as get, patch.object(connect, "_restore_balances"):
            connect._restore_character_assets(self.char1, WALLET)

        get.assert_called_once_with(WALLET, self.char1.key)

    def test_character_balances_come_from_the_mirror(self):
        """The mirror is later than the archive, so it wins."""
        from blockchain.xrpl.models import FungibleGameState

        with patch(
            "blockchain.xrpl.services.nft.NFTService.get_character_nfts",
            return_value=[],
        ), patch.object(connect, "_restore_balances") as balances:
            connect._restore_character_assets(self.char1, WALLET)

        balances.assert_called_once_with(
            self.char1,
            WALLET,
            FungibleGameState.LOCATION_CHARACTER,
            character_key=self.char1.key,
        )

    def test_character_items_take_the_characters_shard(self):
        """An item on a different shard to its holder is a cross-shard FK
        the moment its location is dereferenced."""
        with patch.object(
            connect, "_recovery_shard", return_value="shard0"
        ), patch.object(connect, "_stamping_as") as stamping, patch(
            "typeclasses.items.base_nft_item.BaseNFTItem.spawn_into"
        ), patch(
            "blockchain.xrpl.services.nft.NFTService.get_character_nfts",
            return_value=[type("_Row", (), {"nftoken_id": "TOKENA"})()],
        ), patch.object(connect, "_restore_balances"):
            connect._restore_character_assets(self.char1, WALLET)

        stamping.assert_called_once_with("shard0")

    def test_characters_are_not_left_resident(self):
        """The router must not hold game objects once recovery is done."""
        char = MagicMock()
        char.key = "Fred"

        with patch.object(connect, "_login_account"), patch.object(
            connect, "_reattach_character"
        ):
            connect._on_characters_restored(
                self.fake_session, ADDRESS, self.account, [char]
            )

        char.flush_from_cache.assert_called_once_with(force=True)

    def test_names_are_read_before_the_flush(self):
        """A flushed instance is not worth reading from."""
        char = MagicMock()
        char.key = "Fred"

        with patch.object(connect, "_login_account"), patch.object(
            connect, "_reattach_character"
        ):
            connect._on_characters_restored(
                self.fake_session, ADDRESS, self.account, [char]
            )

        self.assertIn("Fred", self.fake_session.output)

    def test_one_bad_character_does_not_stop_the_others(self):
        """A reattach that raises must not lose the rest of the batch."""
        calls = []

        def _flaky(acct, char):
            calls.append(char)
            if len(calls) == 1:
                raise RuntimeError("this one is broken")

        with patch.object(connect, "_login_account"), patch.object(
            connect, "_reattach_character", side_effect=_flaky
        ), patch.object(connect.logger, "log_err"), patch.object(
            connect.logger, "log_trace"
        ):
            connect._on_characters_restored(
                self.fake_session, ADDRESS, self.account,
                [self.char1, self.char2],
            )

        self.assertEqual(len(calls), 2)


class TestUsernameChecksTheArchive(BaseEvenniaTest):
    """A username held by an archived account is not available.

    After a world rebuild the live database holds no accounts, so every
    username reads as free until its owner signs in. Handing one out in
    that window would force the returning player back as "rowan1".
    """

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.fake_session = FakeSession()
        self.fake_session.ndb.xaman_wallet_address = WALLET
        self.fake_session.ndb.xaman_address = ADDRESS

    def _try(self, username):
        return connect._handle_username_input(self.fake_session, "", username)

    def test_a_live_username_is_refused(self):
        reprompt = self._try(self.account.username)

        self.assertTrue(reprompt, "Should re-prompt for a taken username.")
        self.assertIn("already taken", self.fake_session.output)

    def test_an_archived_username_is_refused(self):
        """The case that only exists after a rebuild."""
        from evennia.accounts.models import AccountDB

        # An archived account with no live counterpart, which is what a
        # rebuild leaves behind.
        AccountDB.objects.using("archive").create(
            username="Awayplayer", db_key="Awayplayer"
        )

        reprompt = self._try("Awayplayer")

        self.assertTrue(reprompt)
        self.assertIn("already taken", self.fake_session.output)

    def test_a_free_username_is_not_refused(self):
        """The check must not refuse everything.

        Account creation is stubbed to fail immediately after the check,
        so this exercises the name validation without building an account.
        """
        Account = connect.class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        with patch.object(
            Account, "create", return_value=(None, ["stopped after the check"])
        ), patch.object(connect, "_clear_xaman_state"):
            self._try("Brandnewname")

        self.assertNotIn("already taken", self.fake_session.output)


class TestArchiveSearchIsScoped(BaseEvenniaTest):
    """The archive search narrows to accounts and keys on the wallet."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_find_is_called_for_accounts_only(self):
        """Left unnarrowed the search would also scan archived objects."""
        with patch("evennia_archive.api.find", return_value=[]) as find:
            connect._find_archived_account(WALLET)

        find.assert_called_once_with(
            "wallet_address", WALLET, model="accountdb"
        )

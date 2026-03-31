"""
Tests for bot management commands: botsetup, botlist, botreset.

evennia test --settings settings tests.command_tests.test_bot_commands
"""

from unittest.mock import patch

from evennia.accounts.models import AccountDB
from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_botsetup import CmdBotSetup
from commands.account_cmds.cmd_botlist import CmdBotList
from commands.account_cmds.cmd_botreset import CmdBotReset


_TEST_USERNAMES = ["test_bot_1", "test_bot_2"]
_TEST_WALLETS = {
    "test_bot_1": "rTestWallet1111111111111111111111",
    "test_bot_2": "rTestWallet2222222222222222222222",
}
_TEST_PASSWORDS = {
    "test_bot_1": "TestBotPass1!",
    "test_bot_2": "TestBotPass2!",
}


def _patch_bot_settings(func):
    """Decorator to patch bot settings for tests."""
    @patch("commands.account_cmds.cmd_botsetup.settings")
    def wrapper(self, mock_settings, *args, **kwargs):
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        mock_settings.BOT_WALLET_ADDRESSES = _TEST_WALLETS
        mock_settings.BOT_PASSWORDS = _TEST_PASSWORDS
        mock_settings.BOT_DEFAULT_PASSWORD = "DefaultPass123!"
        return func(self, mock_settings, *args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


class TestBotSetup(EvenniaCommandTest):
    """Test the botsetup command."""

    def create_script(self):
        pass

    def tearDown(self):
        # Clean up any bot accounts created during tests
        for name in _TEST_USERNAMES:
            account = AccountDB.objects.filter(username=name).first()
            if account:
                # Delete characters first
                for char in account.db._playable_characters or []:
                    if char and char.pk:
                        char.delete()
                account.delete()
        super().tearDown()

    @_patch_bot_settings
    def test_creates_accounts(self, mock_settings):
        """botsetup should create all configured bot accounts."""
        result = self.call(CmdBotSetup(), "")
        self.assertIn("created", result)
        for name in _TEST_USERNAMES:
            account = AccountDB.objects.filter(username=name).first()
            self.assertIsNotNone(account, f"{name} should exist")

    @_patch_bot_settings
    def test_assigns_wallets(self, mock_settings):
        """botsetup should assign wallet addresses from settings."""
        self.call(CmdBotSetup(), "")
        for name, wallet in _TEST_WALLETS.items():
            account = AccountDB.objects.filter(username=name).first()
            self.assertEqual(
                account.attributes.get("wallet_address"), wallet,
                f"{name} should have wallet {wallet}"
            )

    @_patch_bot_settings
    def test_idempotent(self, mock_settings):
        """Running botsetup twice should not create duplicates."""
        self.call(CmdBotSetup(), "")
        result = self.call(CmdBotSetup(), "")
        self.assertIn("already exists", result)
        for name in _TEST_USERNAMES:
            count = AccountDB.objects.filter(username=name).count()
            self.assertEqual(count, 1, f"{name} should exist exactly once")

    @_patch_bot_settings
    def test_updates_wallet_on_existing(self, mock_settings):
        """botsetup should update wallet on existing account if mismatched."""
        # Create account without wallet
        from evennia.utils.create import create_account
        existing = AccountDB.objects.filter(username="test_bot_1").first()
        if existing:
            existing.attributes.remove("wallet_address")
            account = existing
        else:
            account = create_account("test_bot_1", email=None, password="OldPassword123!")

        result = self.call(CmdBotSetup(), "")
        self.assertIn("updated wallet", result)
        account = AccountDB.objects.get(username="test_bot_1")
        self.assertEqual(
            account.attributes.get("wallet_address"),
            _TEST_WALLETS["test_bot_1"],
        )

    @patch("commands.account_cmds.cmd_botsetup.settings")
    def test_no_config(self, mock_settings):
        """botsetup with empty config should show message."""
        mock_settings.BOT_ACCOUNT_USERNAMES = []
        result = self.call(CmdBotSetup(), "")
        self.assertIn("No bot accounts configured", result)

    @_patch_bot_settings
    def test_uses_per_bot_password(self, mock_settings):
        """botsetup should use per-bot password from BOT_PASSWORDS."""
        self.call(CmdBotSetup(), "")
        account = AccountDB.objects.get(username="test_bot_1")
        self.assertTrue(account.check_password("TestBotPass1!"))

    @_patch_bot_settings
    def test_falls_back_to_default_password(self, mock_settings):
        """botsetup should use BOT_DEFAULT_PASSWORD when bot not in BOT_PASSWORDS."""
        mock_settings.BOT_PASSWORDS = {}  # no per-bot passwords
        self.call(CmdBotSetup(), "")
        account = AccountDB.objects.get(username="test_bot_1")
        self.assertTrue(account.check_password("DefaultPass123!"))


class TestBotList(EvenniaCommandTest):
    """Test the botlist command."""

    def create_script(self):
        pass

    def tearDown(self):
        for name in _TEST_USERNAMES:
            account = AccountDB.objects.filter(username=name).first()
            if account:
                for char in account.db._playable_characters or []:
                    if char and char.pk:
                        char.delete()
                account.delete()
        super().tearDown()

    @patch("commands.account_cmds.cmd_botlist.settings")
    def test_shows_not_created(self, mock_settings):
        """botlist should show NOT CREATED for missing accounts."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        mock_settings.BOT_WALLET_ADDRESSES = _TEST_WALLETS
        mock_settings.BOT_LOGIN_ENABLED = True
        result = self.call(CmdBotList(), "")
        self.assertIn("NOT CREATED", result)

    @patch("commands.account_cmds.cmd_botlist.settings")
    def test_shows_existing_account(self, mock_settings):
        """botlist should show details for existing accounts."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        mock_settings.BOT_WALLET_ADDRESSES = _TEST_WALLETS
        mock_settings.BOT_LOGIN_ENABLED = True

        from evennia.utils.create import create_account
        existing = AccountDB.objects.filter(username="test_bot_1").first()
        if existing:
            account = existing
        else:
            account = create_account("test_bot_1", email=None, password="TestPassword123!")
        account.attributes.add("wallet_address", _TEST_WALLETS["test_bot_1"])

        result = self.call(CmdBotList(), "")
        self.assertIn("test_bot_1", result)
        self.assertIn(str(account.id), result)

    @patch("commands.account_cmds.cmd_botlist.settings")
    def test_shows_login_enabled(self, mock_settings):
        """botlist should show BOT_LOGIN_ENABLED status."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        mock_settings.BOT_WALLET_ADDRESSES = _TEST_WALLETS
        mock_settings.BOT_LOGIN_ENABLED = False
        result = self.call(CmdBotList(), "")
        self.assertIn("BOT_LOGIN_ENABLED", result)
        self.assertIn("False", result)

    @patch("commands.account_cmds.cmd_botlist.settings")
    def test_no_config(self, mock_settings):
        """botlist with empty config should show message."""
        mock_settings.BOT_ACCOUNT_USERNAMES = []
        result = self.call(CmdBotList(), "")
        self.assertIn("No bot accounts configured", result)


class TestBotReset(EvenniaCommandTest):
    """Test the botreset command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from evennia.utils.create import create_account
        existing = AccountDB.objects.filter(username="test_bot_1").first()
        if existing:
            self.bot_account = existing
        else:
            self.bot_account = create_account("test_bot_1", email=None, password="TestPassword123!")

    def tearDown(self):
        for name in _TEST_USERNAMES:
            account = AccountDB.objects.filter(username=name).first()
            if account:
                for char in account.db._playable_characters or []:
                    if char and char.pk:
                        char.delete()
                account.delete()
        super().tearDown()

    @patch("commands.account_cmds.cmd_botreset.settings")
    def test_no_args(self, mock_settings):
        """botreset with no args should show usage."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        result = self.call(CmdBotReset(), "")
        self.assertIn("Usage", result)

    @patch("commands.account_cmds.cmd_botreset.settings")
    def test_invalid_name(self, mock_settings):
        """botreset with unknown name should show error."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        result = self.call(CmdBotReset(), "not_a_bot")
        self.assertIn("not in BOT_ACCOUNT_USERNAMES", result)

    @patch("commands.account_cmds.cmd_botreset.settings")
    def test_no_characters(self, mock_settings):
        """botreset on account with no characters should say so."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        result = self.call(CmdBotReset(), "test_bot_1")
        self.assertIn("no characters", result)

    @patch("commands.account_cmds.cmd_botreset.settings")
    def test_deletes_characters(self, mock_settings):
        """botreset should delete all characters on the account."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        # Create a character on the bot account
        char = create.create_object(
            "typeclasses.actors.character.FCMCharacter",
            key="BotChar",
        )
        self.bot_account.db._playable_characters = [char]

        result = self.call(CmdBotReset(), "test_bot_1")
        self.assertIn("deleted character", result)
        self.assertIn("BotChar", result)
        # Account should still exist
        self.assertTrue(AccountDB.objects.filter(username="test_bot_1").exists())

    @patch("commands.account_cmds.cmd_botreset.settings")
    def test_account_not_found(self, mock_settings):
        """botreset on configured but non-existent account should skip."""
        mock_settings.BOT_ACCOUNT_USERNAMES = ["test_bot_2"]
        result = self.call(CmdBotReset(), "test_bot_2")
        self.assertIn("doesn't exist", result)

    @patch("commands.account_cmds.cmd_botreset.settings")
    def test_reset_all(self, mock_settings):
        """botreset all should reset every configured bot."""
        mock_settings.BOT_ACCOUNT_USERNAMES = _TEST_USERNAMES
        result = self.call(CmdBotReset(), "all")
        self.assertIn("Reset complete", result)

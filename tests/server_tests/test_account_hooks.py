"""
Tests for Account hook overrides — superuser language granting, settings usage.

evennia test --settings settings tests.server_tests.test_account_hooks
"""

from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from enums.languages import Languages


class TestSuperuserLanguageGrant(BaseEvenniaTest):
    """at_post_login should grant ALL languages to superuser characters."""

    account_typeclass = "typeclasses.accounts.accounts.Account"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"

    def create_script(self):
        pass

    def test_superuser_gets_all_languages(self):
        """Superuser's characters should receive every language in the enum."""
        self.char1.db.languages = {"common"}

        # Pre-set wallet and bank so those branches don't fire
        self.account.wallet_address = "rTestAddress"
        bank = create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-test",
            nohome=True,
        )
        self.account.db.bank = bank

        with patch.object(
            type(self.account), "is_superuser", new_callable=PropertyMock, return_value=True
        ):
            mock_chars = MagicMock()
            mock_chars.all.return_value = [self.char1]
            with patch.object(
                type(self.account), "characters", new_callable=PropertyMock, return_value=mock_chars
            ):
                self.account.at_post_login(session=MagicMock())

        expected = {lang.value for lang in Languages}
        self.assertEqual(self.char1.db.languages, expected)

    def test_superuser_languages_are_dynamic(self):
        """The enum-based approach means new languages are automatically included."""
        all_lang_values = {lang.value for lang in Languages}
        self.assertIn("common", all_lang_values)
        self.assertIn("dwarven", all_lang_values)
        self.assertIn("dragon", all_lang_values)
        self.assertIn("kobold", all_lang_values)
        self.assertEqual(len(all_lang_values), len(Languages))

    def test_non_superuser_no_language_grant(self):
        """Non-superuser accounts should NOT have languages overwritten."""
        self.char1.db.languages = {"common"}

        self.account.wallet_address = "rTestAddress"
        bank = create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-test2",
            nohome=True,
        )
        self.account.db.bank = bank

        with patch.object(
            type(self.account), "is_superuser", new_callable=PropertyMock, return_value=False
        ):
            self.account.at_post_login(session=MagicMock())

        self.assertEqual(self.char1.db.languages, {"common"})


class TestSettingsUsedInConnect(BaseEvenniaTest):
    """Verify connect command uses settings, not hardcoded values."""

    def create_script(self):
        pass

    def test_setting_exists(self):
        """SUPERUSER_ACCOUNT_NAME should be defined in settings."""
        from django.conf import settings
        self.assertTrue(hasattr(settings, "SUPERUSER_ACCOUNT_NAME"))

    def test_connect_uses_superuser_account_name(self):
        """Connect command func should reference SUPERUSER_ACCOUNT_NAME."""
        import inspect
        from commands.unloggedin_cmds.cmd_override_unconnected_connect import CmdUnconnectedConnect
        source = inspect.getsource(CmdUnconnectedConnect.func)
        self.assertIn("SUPERUSER_ACCOUNT_NAME", source)

    def test_no_hardcoded_password_in_module(self):
        """The module should use DEFAULT_ACCOUNT_PASSWORD, not a hardcoded password."""
        import inspect
        import importlib
        mod = importlib.import_module("commands.unloggedin_cmds.cmd_override_unconnected_connect")
        source = inspect.getsource(mod)
        self.assertIn("DEFAULT_ACCOUNT_PASSWORD", source)
        self.assertNotIn("16*Baird", source)

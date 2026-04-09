"""
Tests for subscription gating on ic, charcreate, chardelete, and import.

Each gated command should show a subscription-expired message when the
account's subscription has expired, and proceed normally when active.

evennia test --settings settings tests.command_tests.test_subscription_gating
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_override_charcreate import CmdCharCreate
from commands.account_cmds.cmd_override_chardelete import CmdCharDelete
from commands.account_cmds.cmd_override_ic import CmdIC
from commands.account_cmds.cmd_import import CmdImport


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
EXPIRED_MSG = "Your subscription has expired."


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestICGating(EvenniaCommandTest):
    """Test that ic is gated by subscription status."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_ic_blocked_when_expired(self):
        """ic should show expired message when subscription expired."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        self.call(
            CmdIC(), "",
            EXPIRED_MSG,
            caller=self.account,
        )

    def test_ic_blocked_when_no_expiry(self):
        """ic should show expired message when no expiry set."""
        self.account.subscription_expires_date = None
        self.call(
            CmdIC(), "",
            EXPIRED_MSG,
            caller=self.account,
        )

    def test_ic_allowed_when_subscribed(self):
        """ic should proceed when subscription is active."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) + timedelta(days=10)
        )
        # With a valid subscription, ic will try to find the character
        # and show "Usage: ic <character>" or similar — NOT the expired msg
        result = self.call(
            CmdIC(), "",
            caller=self.account,
        )
        self.assertNotIn("subscription has expired", result.lower())

    def test_ic_allowed_for_superuser(self):
        """Superuser should bypass subscription check."""
        self.account.is_superuser = True
        self.account.subscription_expires_date = None
        result = self.call(
            CmdIC(), "",
            caller=self.account,
        )
        self.assertNotIn("subscription has expired", result.lower())


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestCharCreateGating(EvenniaCommandTest):
    """Test that charcreate is gated by subscription status."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_charcreate_blocked_when_expired(self):
        """charcreate should show expired message when subscription expired."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        self.call(
            CmdCharCreate(), "",
            EXPIRED_MSG,
            caller=self.account,
        )

    def test_charcreate_blocked_when_no_expiry(self):
        """charcreate should show expired message when no expiry set."""
        self.account.subscription_expires_date = None
        self.call(
            CmdCharCreate(), "",
            EXPIRED_MSG,
            caller=self.account,
        )


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestCharDeleteGating(EvenniaCommandTest):
    """Test that chardelete is gated by subscription status."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_chardelete_blocked_when_expired(self):
        """chardelete should show expired message when subscription expired."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        self.call(
            CmdCharDelete(), "TestChar",
            EXPIRED_MSG,
            caller=self.account,
        )

    def test_chardelete_blocked_when_no_expiry(self):
        """chardelete should show expired message when no expiry set."""
        self.account.subscription_expires_date = None
        self.call(
            CmdCharDelete(), "TestChar",
            EXPIRED_MSG,
            caller=self.account,
        )


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestImportGating(EvenniaCommandTest):
    """Test that import is gated by subscription status."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    @patch("commands.account_cmds.cmd_import.settings")
    def test_import_blocked_when_expired(self, mock_settings):
        """import should show expired message when subscription expired."""
        mock_settings.XRPL_IMPORT_EXPORT_ENABLED = True
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        self.call(
            CmdImport(), "gold 100",
            EXPIRED_MSG,
            caller=self.account,
        )

    @patch("commands.account_cmds.cmd_import.settings")
    def test_import_blocked_when_no_expiry(self, mock_settings):
        """import should show expired message when no expiry set."""
        mock_settings.XRPL_IMPORT_EXPORT_ENABLED = True
        self.account.subscription_expires_date = None
        self.call(
            CmdImport(), "gold 100",
            EXPIRED_MSG,
            caller=self.account,
        )


class TestGatingBypassWhenDisabled(EvenniaCommandTest):
    """With SUBSCRIPTION_ENABLED=False (default), gated commands bypass checks."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.subscription_expires_date = None

    def test_ic_bypasses_when_disabled(self):
        """ic should not show expired message when subscriptions disabled."""
        result = self.call(
            CmdIC(), "",
            caller=self.account,
        )
        self.assertNotIn("subscription has expired", result.lower())

    def test_charcreate_bypasses_when_disabled(self):
        """charcreate should not show expired message when subscriptions disabled."""
        result = self.call(
            CmdCharCreate(), "",
            caller=self.account,
        )
        self.assertNotIn("subscription has expired", result.lower())

    def test_chardelete_bypasses_when_disabled(self):
        """chardelete should not show expired message when subscriptions disabled."""
        result = self.call(
            CmdCharDelete(), "TestChar",
            caller=self.account,
        )
        self.assertNotIn("subscription has expired", result.lower())

"""
Tests for the subscribe command.

The command uses get_input() + deferToThread for the Xaman payment flow,
which can't be fully tested via EvenniaCommandTest.call(). We test:
  1. Early-return paths (no wallet, exempt account) via call()
  2. Subscription utils integration (already tested in test_subscription_utils)

evennia test --settings settings tests.command_tests.test_cmd_subscribe
"""

from datetime import datetime, timedelta, timezone

from django.test import override_settings
from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_subscribe import CmdSubscribe


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestCmdSubscribeEarlyReturns(EvenniaCommandTest):
    """Test subscribe command early-return paths."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_wallet_shows_error(self):
        """subscribe with no wallet linked shows error."""
        self.account.wallet_address = ""
        self.call(
            CmdSubscribe(), "",
            "No wallet linked to your account.",
            caller=self.account,
        )

    def test_exempt_account_shows_message(self):
        """Superuser told they don't need a subscription."""
        self.account.is_superuser = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.call(
            CmdSubscribe(), "",
            "Your account does not require a subscription.",
            caller=self.account,
        )

    def test_shows_current_status_when_subscribed(self):
        """Active subscriber sees their expiry when running subscribe."""
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) + timedelta(days=20)
        )
        result = self.call(
            CmdSubscribe(), "",
            caller=self.account,
        )
        self.assertIn("You are subscribed until", result)

    def test_shows_not_subscribed_when_expired(self):
        """Expired subscriber sees not-subscribed message."""
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        result = self.call(
            CmdSubscribe(), "",
            caller=self.account,
        )
        self.assertIn("You are not currently subscribed", result)


class TestCmdSubscribeWhenDisabled(EvenniaCommandTest):
    """Test subscribe command when SUBSCRIPTION_ENABLED is False."""

    def create_script(self):
        pass

    def test_subscribe_shows_not_active(self):
        """subscribe should show not-active message when disabled."""
        self.account.attributes.add("wallet_address", WALLET_A)
        self.call(
            CmdSubscribe(), "",
            "Subscriptions are not currently active.",
            caller=self.account,
        )

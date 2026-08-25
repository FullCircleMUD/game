"""
Tests for the subscribe command.

The command uses get_input() + deferToThread for the Xaman payment flow,
which can't be fully tested via EvenniaCommandTest.call(). We test:
  1. Early-return paths (no wallet, exempt account) via call()
  2. Subscription utils integration (already tested in test_subscription_utils)

evennia test --settings settings tests.command_tests.test_cmd_subscribe
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaCommandTest

import commands.account_cmds.cmd_subscribe as subscribe_module
from commands.account_cmds.cmd_subscribe import CmdSubscribe


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class _Plan:
    """The fields _on_payment_verified reads off a SubscriptionPlan."""

    key = "monthly"
    duration_days = 30
    price = 20


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestPaymentRefreshesTheArchive(EvenniaCommandTest):
    """A payment archives the account rather than waiting for logout.

    The session-end archive would catch the new expiry eventually. A
    player who pays and then loses the server before logging out would be
    restored on their old expiry, having paid — so this one change gets
    its own call.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.subscription_expires_date = None

    def _pay(self):
        with patch.object(
            subscribe_module, "_connected", return_value=True
        ), patch.object(
            type(self.account), "archive_now"
        ) as archive_now:
            subscribe_module._on_payment_verified(
                self.account, _Plan(), "RLUSD", "HASHSUBSCRIBEARCHIVE", 20
            )
        return archive_now

    def test_payment_archives_the_account(self):
        self._pay().assert_called_once()

    def test_payment_extends_the_expiry_first(self):
        """The archive must capture the new expiry, not the old one."""
        self._pay()
        self.assertIsNotNone(self.account.subscription_expires_date)

    def test_payment_row_is_written_before_the_archive(self):
        """Both records exist by the time the copy is taken."""
        from subscriptions.models import SubscriptionPayment

        self._pay()

        self.assertTrue(
            SubscriptionPayment.objects.using("subscriptions")
            .filter(tx_hash="HASHSUBSCRIBEARCHIVE")
            .exists()
        )


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

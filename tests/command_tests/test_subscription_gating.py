"""
Tests for subscription gating on ic, charcreate, chardelete, import,
and export.

Each gated command should show a subscription-expired message when the
account's subscription has expired, and proceed normally when active.

Export uses a different gate: blocked while the account is on a free
trial (has_paid=False), but allowed forever once any payment is on
record — even after the subscription expires.

evennia test --settings settings tests.command_tests.test_subscription_gating
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmd_export import CmdExport
from commands.account_cmds.cmd_import import CmdImport
from commands.account_cmds.cmd_override_charcreate import CmdCharCreate
from commands.account_cmds.cmd_override_chardelete import CmdCharDelete
from commands.account_cmds.cmd_override_ic import CmdIC


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


@override_settings(
    SUBSCRIPTION_ENABLED=True,
    XRPL_IMPORT_EXPORT_ENABLED=True,
)
class TestExportGating(EvenniaCommandTest):
    """
    Test that export is gated by has_paid only — not by subscription
    expiry. A paid player must never be trapped with their assets.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.is_superuser = False
        # Clear any payment rows from prior tests
        from subscriptions.models import SubscriptionPayment
        SubscriptionPayment.objects.using("subscriptions").filter(
            account_id=self.account.id
        ).delete()

    def _record_payment(self):
        """Helper: insert a SubscriptionPayment so has_paid() returns True."""
        from subscriptions.models import SubscriptionPayment
        SubscriptionPayment.objects.using("subscriptions").create(
            account_id=self.account.id,
            account_name=self.account.key,
            wallet_address=WALLET_A,
            plan_key="monthly",
            amount=20,
            currency_code="RLUSD",
            tx_hash=f"HASHEXPORTTEST{self.account.id}",
            old_expiry=None,
            new_expiry=datetime.now(timezone.utc) + timedelta(days=30),
        )

    def test_export_blocked_for_free_trial(self):
        """Free-trial account (no payment record) should be blocked."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) + timedelta(hours=24)
        )
        self.call(
            CmdExport(), "gold 10",
            "Export is not available during the free trial.",
            caller=self.account,
        )

    def test_export_blocked_with_no_expiry_and_no_payment(self):
        """Account with no expiry and no payments is blocked."""
        self.account.subscription_expires_date = None
        self.call(
            CmdExport(), "gold 10",
            "Export is not available during the free trial.",
            caller=self.account,
        )

    def test_export_allowed_after_payment_even_if_expired(self):
        """
        Once a player has paid at least once, export stays available even
        after their subscription has lapsed. This is the no-trap promise.
        """
        self._record_payment()
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(days=10)
        )
        result = self.call(
            CmdExport(), "gold 10",
            caller=self.account,
        )
        self.assertNotIn(
            "Export is not available during the free trial",
            result,
        )

    def test_export_allowed_after_payment_while_subscribed(self):
        """Paid + active subscription should bypass the trial gate."""
        self._record_payment()
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) + timedelta(days=10)
        )
        result = self.call(
            CmdExport(), "gold 10",
            caller=self.account,
        )
        self.assertNotIn(
            "Export is not available during the free trial",
            result,
        )

    def test_export_allowed_for_superuser(self):
        """Superuser is treated as paid (via _is_exempt → has_paid)."""
        self.account.is_superuser = True
        self.account.subscription_expires_date = None
        result = self.call(
            CmdExport(), "gold 10",
            caller=self.account,
        )
        self.assertNotIn(
            "Export is not available during the free trial",
            result,
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

    @override_settings(XRPL_IMPORT_EXPORT_ENABLED=True)
    def test_export_bypasses_trial_gate_when_disabled(self):
        """
        With SUBSCRIPTION_ENABLED=False, has_paid() returns True for
        everyone via _is_exempt, so the trial gate is inert and export
        falls through to the next checks.
        """
        result = self.call(
            CmdExport(), "gold 10",
            caller=self.account,
        )
        self.assertNotIn(
            "Export is not available during the free trial",
            result,
        )

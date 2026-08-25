"""
Tests for subscriptions.utils — is_subscribed, get_subscription_status,
extend_subscription, grant_trial, has_had_trial, has_paid, _is_exempt.

A trial is recorded as a zero-amount row in the payment log, keyed on the
wallet. That makes it survive a world rebuild and makes one-trial-per-
wallet enforceable; it also means has_paid() has to exclude those rows,
because has_paid gates export.

evennia test --settings settings tests.command_tests.test_subscription_utils
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.test_resources import EvenniaTest

from subscriptions.utils import (
    TRIAL_PLAN_KEY,
    _is_exempt,
    extend_subscription,
    get_subscription_status,
    grant_trial,
    has_had_trial,
    has_paid,
    is_subscribed,
)


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
WALLET_C = "0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"


def _clear_payments(*wallets):
    """Remove payment rows for these wallets.

    Scoped by wallet rather than account id, because that is what every
    query in subscriptions.utils now keys on — a trial row left behind
    under the same wallet would silently refuse the next trial.
    """
    from subscriptions.models import SubscriptionPayment

    SubscriptionPayment.objects.using("subscriptions").filter(
        wallet_address__in=wallets
    ).delete()


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestIsSubscribed(EvenniaTest):
    """Test is_subscribed() under various conditions."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_no_expiry_returns_false(self):
        """Account with no expiry is not subscribed."""
        self.account.subscription_expires_date = None
        self.assertFalse(is_subscribed(self.account))

    def test_future_expiry_returns_true(self):
        """Account with future expiry is subscribed."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) + timedelta(days=10)
        )
        self.assertTrue(is_subscribed(self.account))

    def test_past_expiry_returns_false(self):
        """Account with past expiry is not subscribed."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(hours=1)
        )
        self.assertFalse(is_subscribed(self.account))

    def test_superuser_always_subscribed(self):
        """Superuser account is always subscribed regardless of expiry."""
        self.account.is_superuser = True
        self.account.subscription_expires_date = None
        self.assertTrue(is_subscribed(self.account))

    @patch("subscriptions.utils.settings")
    def test_bot_account_always_subscribed(self, mock_settings):
        """Bot accounts bypass subscription check."""
        mock_settings.SUBSCRIPTION_BYPASS_SUPERUSER = True
        mock_settings.BOT_ACCOUNT_USERNAMES = [self.account.key]
        self.account.subscription_expires_date = None
        self.assertTrue(is_subscribed(self.account))


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestGetSubscriptionStatus(EvenniaTest):
    """Test get_subscription_status() returns correct dicts."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_exempt_status(self):
        """Superuser gets exempt status."""
        self.account.is_superuser = True
        status = get_subscription_status(self.account)
        self.assertTrue(status["is_exempt"])
        self.assertTrue(status["subscribed"])
        self.assertIsNone(status["expiry"])
        self.assertFalse(status["is_warning"])

    def test_no_expiry_status(self):
        """No expiry set returns unsubscribed."""
        self.account.subscription_expires_date = None
        status = get_subscription_status(self.account)
        self.assertFalse(status["subscribed"])
        self.assertIsNone(status["expiry"])
        self.assertFalse(status["is_exempt"])

    def test_expired_status(self):
        """Past expiry returns unsubscribed with 0 hours remaining."""
        expiry = datetime.now(timezone.utc) - timedelta(hours=1)
        self.account.subscription_expires_date = expiry
        status = get_subscription_status(self.account)
        self.assertFalse(status["subscribed"])
        self.assertEqual(status["hours_remaining"], 0)

    def test_active_no_warning(self):
        """Active subscription with > 48h remaining: no warning."""
        expiry = datetime.now(timezone.utc) + timedelta(days=20)
        self.account.subscription_expires_date = expiry
        status = get_subscription_status(self.account)
        self.assertTrue(status["subscribed"])
        self.assertFalse(status["is_warning"])
        self.assertGreater(status["hours_remaining"], 48)

    def test_active_with_warning(self):
        """Active subscription with < 48h remaining: warning flag."""
        expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        self.account.subscription_expires_date = expiry
        status = get_subscription_status(self.account)
        self.assertTrue(status["subscribed"])
        self.assertTrue(status["is_warning"])
        self.assertLess(status["hours_remaining"], 48)


class TestExtendSubscription(EvenniaTest):
    """Test extend_subscription() logic."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_extend_from_now_when_expired(self):
        """Expired account extends from now, not from old expiry."""
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(days=5)
        )
        before = datetime.now(timezone.utc)
        new_expiry = extend_subscription(self.account, 30)
        after = datetime.now(timezone.utc)

        # New expiry should be ~30 days from now
        self.assertGreaterEqual(new_expiry, before + timedelta(days=30))
        self.assertLessEqual(new_expiry, after + timedelta(days=30))

    def test_extend_from_now_when_no_expiry(self):
        """No prior expiry extends from now."""
        self.account.subscription_expires_date = None
        before = datetime.now(timezone.utc)
        new_expiry = extend_subscription(self.account, 30)
        after = datetime.now(timezone.utc)

        self.assertGreaterEqual(new_expiry, before + timedelta(days=30))
        self.assertLessEqual(new_expiry, after + timedelta(days=30))

    def test_extend_from_current_expiry_when_active(self):
        """Active subscription extends from current expiry."""
        future_expiry = datetime.now(timezone.utc) + timedelta(days=10)
        self.account.subscription_expires_date = future_expiry
        new_expiry = extend_subscription(self.account, 30)

        expected = future_expiry + timedelta(days=30)
        self.assertAlmostEqual(
            new_expiry.timestamp(), expected.timestamp(), delta=2
        )

    def test_extend_updates_attribute(self):
        """extend_subscription persists the new expiry on the account."""
        self.account.subscription_expires_date = None
        new_expiry = extend_subscription(self.account, 30)
        self.assertEqual(self.account.subscription_expires_date, new_expiry)


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestGrantTrial(EvenniaTest):
    """Test grant_trial() logic."""

    # grant_trial writes the trial to the subscriptions database, so this
    # class touches more than `default`.
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        _clear_payments(WALLET_A)

    def test_grant_trial_sets_expiry(self):
        """Trial sets expiry to now + trial hours."""
        self.account.subscription_expires_date = None
        before = datetime.now(timezone.utc)
        result = grant_trial(self.account)
        after = datetime.now(timezone.utc)

        self.assertIsNotNone(result)
        self.assertGreaterEqual(result, before + timedelta(hours=48))
        self.assertLessEqual(result, after + timedelta(hours=48))

    def test_grant_trial_noop_if_already_set(self):
        """Trial is no-op if account already has expiry."""
        existing = datetime.now(timezone.utc) + timedelta(days=30)
        self.account.subscription_expires_date = existing
        result = grant_trial(self.account)
        self.assertIsNone(result)
        self.assertEqual(
            self.account.subscription_expires_date, existing
        )

    @patch("subscriptions.utils.settings")
    def test_grant_trial_noop_if_zero_hours(self, mock_settings):
        """Trial is no-op if SUBSCRIPTION_TRIAL_HOURS is 0."""
        mock_settings.SUBSCRIPTION_TRIAL_HOURS = 0
        self.account.subscription_expires_date = None
        result = grant_trial(self.account)
        self.assertIsNone(result)
        self.assertIsNone(self.account.subscription_expires_date)


class TestSubscriptionDisabled(EvenniaTest):
    """Test behaviour when SUBSCRIPTION_ENABLED is False (default)."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_is_exempt_returns_true_when_disabled(self):
        """Everyone is exempt when subscriptions are disabled."""
        self.account.subscription_expires_date = None
        self.assertTrue(_is_exempt(self.account))

    def test_is_subscribed_returns_true_when_disabled(self):
        """Everyone appears subscribed when subscriptions are disabled."""
        self.account.subscription_expires_date = None
        self.assertTrue(is_subscribed(self.account))

    def test_grant_trial_noop_when_disabled(self):
        """Trial is not granted when subscriptions are disabled."""
        self.account.subscription_expires_date = None
        result = grant_trial(self.account)
        self.assertIsNone(result)
        self.assertIsNone(self.account.subscription_expires_date)

    def test_get_status_shows_exempt_when_disabled(self):
        """Status shows exempt for everyone when subscriptions are disabled."""
        self.account.subscription_expires_date = None
        status = get_subscription_status(self.account)
        self.assertTrue(status["is_exempt"])
        self.assertTrue(status["subscribed"])

    @override_settings(SUBSCRIPTION_ENABLED=True)
    def test_is_exempt_checks_normally_when_enabled(self):
        """Normal accounts are NOT exempt when subscriptions are enabled."""
        self.account.is_superuser = False
        self.assertFalse(_is_exempt(self.account))


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestHasPaid(EvenniaTest):
    """Test has_paid() under various conditions."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.is_superuser = False
        # Clear any payment records left from prior tests
        _clear_payments(WALLET_A)

    def test_no_payment_returns_false(self):
        """Account that has never paid returns False."""
        self.assertFalse(has_paid(self.account))

    def test_with_payment_returns_true(self):
        """Account with at least one payment returns True."""
        from subscriptions.models import SubscriptionPayment
        from datetime import datetime, timedelta, timezone

        SubscriptionPayment.objects.using("subscriptions").create(
            account_id=self.account.id,
            account_name=self.account.key,
            wallet_address=WALLET_A,
            plan_key="monthly",
            amount=20,
            currency_code="RLUSD",
            tx_hash="HASHHASPAIDTEST1",
            old_expiry=None,
            new_expiry=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.assertTrue(has_paid(self.account))

    def test_superuser_returns_true_without_payment(self):
        """Superuser is treated as paid even with no payment record."""
        self.account.is_superuser = True
        self.assertTrue(has_paid(self.account))

    def test_payment_persists_after_expiry(self):
        """has_paid stays True even after subscription has expired."""
        from subscriptions.models import SubscriptionPayment
        from datetime import datetime, timedelta, timezone

        SubscriptionPayment.objects.using("subscriptions").create(
            account_id=self.account.id,
            account_name=self.account.key,
            wallet_address=WALLET_A,
            plan_key="monthly",
            amount=20,
            currency_code="RLUSD",
            tx_hash="HASHHASPAIDTEST2",
            old_expiry=None,
            new_expiry=datetime.now(timezone.utc) - timedelta(days=30),
        )
        self.account.subscription_expires_date = (
            datetime.now(timezone.utc) - timedelta(days=10)
        )
        # Subscription expired, but they have a payment on record
        self.assertFalse(is_subscribed(self.account))
        self.assertTrue(has_paid(self.account))


class TestHasPaidWhenDisabled(EvenniaTest):
    """has_paid() returns True for everyone when SUBSCRIPTION_ENABLED=False."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_has_paid_returns_true_when_disabled(self):
        """With subscriptions disabled, every account is treated as paid."""
        self.account.is_superuser = False
        self.assertTrue(has_paid(self.account))


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestTrialIsRecorded(EvenniaTest):
    """A granted trial writes a durable row to the payment log.

    The row is the point: the account attribute holding the expiry is
    destroyed by a world rebuild, and this is what survives it.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.subscription_expires_date = None
        _clear_payments(WALLET_A, WALLET_B, WALLET_C)

    def _trial_rows(self, wallet):
        from subscriptions.models import SubscriptionPayment

        return list(
            SubscriptionPayment.objects.using("subscriptions").filter(
                wallet_address=wallet, plan_key=TRIAL_PLAN_KEY
            )
        )

    def test_trial_writes_one_row(self):
        """Granting a trial records exactly one row for that wallet."""
        expiry = grant_trial(self.account)
        rows = self._trial_rows(WALLET_A)

        self.assertIsNotNone(expiry)
        self.assertEqual(len(rows), 1)

    def test_trial_row_shape(self):
        """The row carries the trial's terms, not a payment's."""
        expiry = grant_trial(self.account)
        row = self._trial_rows(WALLET_A)[0]

        self.assertEqual(row.plan_key, TRIAL_PLAN_KEY)
        self.assertEqual(row.amount, 0)
        self.assertEqual(row.wallet_address, WALLET_A)
        self.assertIsNone(row.old_expiry)
        self.assertAlmostEqual(
            row.new_expiry.timestamp(), expiry.timestamp(), delta=2
        )

    def test_trial_tx_hash_is_derived_from_wallet(self):
        """tx_hash is unique, so deriving it makes a second trial impossible."""
        grant_trial(self.account)
        row = self._trial_rows(WALLET_A)[0]

        self.assertEqual(row.tx_hash, f"{TRIAL_PLAN_KEY}:{WALLET_A}")

    def test_no_wallet_grants_expiry_but_writes_no_row(self):
        """A walletless account still gets its trial, with nothing to key on.

        Writing the row would mean a tx_hash of "trial:None", which the
        unique constraint would let exactly one account hold — and the
        next one would fail account creation outright.
        """
        self.account.attributes.remove("wallet_address")
        self.account.subscription_expires_date = None

        expiry = grant_trial(self.account)

        self.assertIsNotNone(expiry)
        self.assertEqual(self._trial_rows(None), [])

    def test_has_had_trial_false_before(self):
        """An unknown wallet has not had a trial."""
        self.assertFalse(has_had_trial(WALLET_B))

    def test_has_had_trial_true_after(self):
        """The wallet that was granted a trial reports it."""
        grant_trial(self.account)
        self.assertTrue(has_had_trial(WALLET_A))

    def test_has_had_trial_false_for_no_wallet(self):
        """No wallet is not an error, and is not a prior trial."""
        self.assertFalse(has_had_trial(None))
        self.assertFalse(has_had_trial(""))


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestTrialCannotBeTakenTwice(EvenniaTest):
    """One trial per wallet, across accounts and across rebuilds."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.subscription_expires_date = None
        _clear_payments(WALLET_A)

    def test_second_trial_on_same_account_refused(self):
        """Clearing the expiry does not buy a second trial."""
        first = grant_trial(self.account)
        self.assertIsNotNone(first)

        # Wipe the fast path so only the wallet gate can refuse.
        self.account.subscription_expires_date = None
        second = grant_trial(self.account)

        self.assertIsNone(second)
        self.assertIsNone(self.account.subscription_expires_date)

    def test_second_trial_on_a_new_account_refused(self):
        """The rebuild case: fresh account, same wallet, no second trial.

        This is what the payment row exists for. A world rebuild frees
        every account, so without a wallet-keyed record the same player
        could take a new trial after every rebuild.
        """
        grant_trial(self.account)

        from evennia.utils import create as evennia_create

        newcomer = evennia_create.create_account(
            "trialfarmer", "farmer@example.com", "pw12345678xyz"
        )
        newcomer.attributes.add("wallet_address", WALLET_A)
        newcomer.subscription_expires_date = None

        self.assertIsNone(grant_trial(newcomer))
        self.assertIsNone(newcomer.subscription_expires_date)

    def test_a_different_wallet_still_gets_its_trial(self):
        """The gate is per wallet, not global."""
        grant_trial(self.account)

        self.account.attributes.add("wallet_address", WALLET_B)
        self.account.subscription_expires_date = None

        self.assertIsNotNone(grant_trial(self.account))


@override_settings(SUBSCRIPTION_ENABLED=True)
class TestHasPaidIgnoresTrials(EvenniaTest):
    """has_paid() gates export, so a trial must never satisfy it."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account.is_superuser = False
        self.account.subscription_expires_date = None
        _clear_payments(WALLET_A)

    def test_trial_alone_is_not_paid(self):
        """A trial row must not open export to someone who never paid."""
        grant_trial(self.account)
        self.assertTrue(has_had_trial(WALLET_A))
        self.assertFalse(has_paid(self.account))

    def test_payment_after_trial_is_paid(self):
        """A real payment alongside the trial row still counts."""
        from subscriptions.models import SubscriptionPayment

        grant_trial(self.account)
        SubscriptionPayment.objects.using("subscriptions").create(
            account_id=self.account.id,
            account_name=self.account.key,
            wallet_address=WALLET_A,
            plan_key="monthly",
            amount=20,
            currency_code="RLUSD",
            tx_hash="HASHTRIALTHENPAID",
            old_expiry=None,
            new_expiry=datetime.now(timezone.utc) + timedelta(days=30),
        )

        self.assertTrue(has_paid(self.account))

    def test_payment_under_a_different_account_id_still_counts(self):
        """The rebuild case: same wallet, new primary key, still paid.

        Keying on account_id would report a player who has paid for a
        year as never having paid, and silently close export to them.
        """
        from subscriptions.models import SubscriptionPayment

        SubscriptionPayment.objects.using("subscriptions").create(
            account_id=self.account.id + 9999,
            account_name="whatever-they-were-called-before",
            wallet_address=WALLET_A,
            plan_key="monthly",
            amount=20,
            currency_code="RLUSD",
            tx_hash="HASHREBUILTACCOUNT",
            old_expiry=None,
            new_expiry=datetime.now(timezone.utc) + timedelta(days=30),
        )

        self.assertTrue(has_paid(self.account))

    def test_no_wallet_is_not_paid(self):
        """Without a wallet there is nothing to match, so nothing is proven."""
        self.account.attributes.remove("wallet_address")
        self.assertFalse(has_paid(self.account))

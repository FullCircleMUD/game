"""
Tests what Account.create() does after the account row exists.

Two things hang off the tail of ``Account.create()`` rather than off
``at_account_creation``, and both are there for the same reason: the
wallet address is assigned *after* ``create_account()`` returns, so
inside the creation hook it still reads ``None``.

- the free trial, which is keyed on the wallet
- the archive copy, which is found by the wallet

Either one moved back into the hook would keep working in the sense of
not raising, and would silently record ``None`` where the wallet should
be. That is what these tests exist to catch.

The archive write is dispatched with ``deferToThread``; the tests patch
that to run inline, so the assertion lands in the same call.

evennia test --settings settings tests.server_tests.test_account_create_wiring
"""

from unittest.mock import PropertyMock, patch

from django.conf import settings
from django.test import override_settings
from evennia.utils.test_resources import BaseEvenniaTest
from twisted.internet import defer

from subscriptions.utils import TRIAL_PLAN_KEY


WALLET = "rAccountCreateWiringTestWallet1"
PASSWORD = "correct-horse-battery-staple"


def _sync_defer(func, *args, **kwargs):
    """Run *func* synchronously and return an already-fired Deferred."""
    d = defer.Deferred()
    try:
        result = func(*args, **kwargs)
        d.callback(result)
    except Exception as e:
        d.errback(e)
    return d


def _account_class(test):
    """The FCM Account typeclass this test case is configured with.

    Read off the test case rather than settings.BASE_ACCOUNT_TYPECLASS —
    Evennia's test resources point that at DefaultAccount, which has none
    of the behaviour under test here.
    """
    from evennia.utils import class_from_module

    typeclass = test.account_typeclass
    if isinstance(typeclass, str):
        return class_from_module(typeclass)
    return typeclass


def _clear_payments(wallet):
    from subscriptions.models import SubscriptionPayment

    SubscriptionPayment.objects.using("subscriptions").filter(
        wallet_address=wallet
    ).delete()


@override_settings(SUBSCRIPTION_ENABLED=True)
@patch("typeclasses.accounts.accounts.threads.deferToThread", _sync_defer)
class TestAccountCreateWiring(BaseEvenniaTest):
    """The tail of Account.create() grants the trial and archives."""

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        _clear_payments(WALLET)

    def tearDown(self):
        _clear_payments(WALLET)
        super().tearDown()

    def _create(self, username, **kwargs):
        account, errors = _account_class(self).create(
            username=username,
            password=PASSWORD,
            wallet_address=kwargs.pop("wallet_address", WALLET),
            **kwargs,
        )
        self.assertIsNotNone(
            account, f"Account.create() failed: {errors}"
        )
        return account

    def test_wallet_is_set_on_the_created_account(self):
        """The premise the other tests rest on."""
        account = self._create("wiringwallet")
        self.assertEqual(account.wallet_address, WALLET)

    def test_trial_is_granted(self):
        """grant_trial moved to the tail of create(); it must still run."""
        account = self._create("wiringtrial")
        self.assertIsNotNone(
            account.subscription_expires_date,
            "No trial was granted. grant_trial() is called from the tail "
            "of Account.create() — check it was not lost in a refactor.",
        )

    def test_trial_is_recorded_against_the_wallet(self):
        """The durable record must carry the wallet, not None.

        This is the failure the move exists to prevent: run grant_trial
        from at_account_creation and the row is written before
        wallet_address is assigned.
        """
        from subscriptions.models import SubscriptionPayment

        self._create("wiringtrialrow")

        row = (
            SubscriptionPayment.objects.using("subscriptions")
            .filter(wallet_address=WALLET, plan_key=TRIAL_PLAN_KEY)
            .first()
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.tx_hash, f"{TRIAL_PLAN_KEY}:{WALLET}")

    def test_account_is_archived(self):
        """The archived copy is what a world rebuild recovers from."""
        from evennia_archive.models import ArchiveRecord

        account = self._create("wiringarchive")

        self.assertIsNotNone(account.archive_id)
        self.assertTrue(
            ArchiveRecord.objects.using("archive")
            .filter(pk=account.archive_id)
            .exists(),
            "Account.create() did not archive the new account.",
        )

    def test_archived_copy_carries_the_wallet(self):
        """Archived without a wallet is archived unfindable.

        The login flow searches the archive by wallet address. A copy
        written before wallet_address was assigned is present, correct
        in every other respect, and can never be restored.
        """
        from evennia.accounts.models import AccountDB
        from evennia_archive.models import ArchiveRecord

        account = self._create("wiringarchivewallet")
        record = ArchiveRecord.objects.using("archive").get(
            pk=account.archive_id
        )

        stored = (
            AccountDB.objects.using("archive")
            .filter(
                pk=record.archived_pk,
                db_attributes__db_key="wallet_address",
            )
            .exists()
        )
        self.assertTrue(
            stored, "The archived account has no wallet_address attribute."
        )

    def test_archive_failure_does_not_break_account_creation(self):
        """A failed archive is logged, never fatal.

        The account is re-archived at first logout, so losing this copy
        self-heals. Refusing to create the account would not.
        """
        with patch(
            "evennia_archive.api.archive",
            side_effect=RuntimeError("archive is down"),
        ):
            account = self._create("wiringarchivefails")

        self.assertIsNotNone(account)
        self.assertIsNotNone(account.subscription_expires_date)


@override_settings(SUBSCRIPTION_ENABLED=True)
@patch("typeclasses.accounts.accounts.threads.deferToThread", _sync_defer)
class TestSuperuserGetsNoTrial(BaseEvenniaTest):
    """The superuser guard came across with the moved call.

    In at_account_creation the trial sat inside ``if not
    self.is_superuser``. grant_trial does not check exemption itself, so
    the guard had to be restated at the new call site — without it an
    exempt account burns the one trial its wallet is allowed.
    """

    account_typeclass = "typeclasses.accounts.accounts.Account"
    databases = "__all__"

    def create_script(self):
        pass

    def tearDown(self):
        _clear_payments(WALLET)
        super().tearDown()

    def _create(self, username):
        # Resolved from the class attribute, not BASE_ACCOUNT_TYPECLASS:
        # Evennia's test resources point that setting at DefaultAccount,
        # so using it would exercise Evennia's create() and never reach
        # the FCM tail these tests are about.
        account, errors = _account_class(self).create(
            username=username,
            password=PASSWORD,
            wallet_address=WALLET,
        )
        self.assertIsNotNone(account, f"create() failed: {errors}")
        return account

    def test_superuser_creation_grants_no_trial(self):
        """An exempt account must not burn the wallet's one trial."""
        from evennia.accounts.models import AccountDB
        from subscriptions.models import SubscriptionPayment

        with patch.object(
            AccountDB,
            "is_superuser",
            new_callable=PropertyMock,
            return_value=True,
        ):
            account = self._create("wiringsuperuser")

        self.assertIsNone(account.subscription_expires_date)
        self.assertFalse(
            SubscriptionPayment.objects.using("subscriptions")
            .filter(wallet_address=WALLET, plan_key=TRIAL_PLAN_KEY)
            .exists(),
            "A trial row was written for an exempt account, consuming the "
            "one trial that wallet is allowed.",
        )

    def test_a_normal_account_does_get_the_trial(self):
        """The control.

        Without it, the test above also passes when the grant_trial call
        has been deleted outright rather than guarded.
        """
        account = self._create("wiringnotsuperuser")
        self.assertIsNotNone(account.subscription_expires_date)

"""
Subscription status utilities.

Every subscription check in the codebase goes through this module.
"""

from datetime import datetime, timedelta, timezone

from django.conf import settings

# The plan_key a trial's SubscriptionPayment row carries. It is not a
# SubscriptionPlan — nothing offers it for purchase — it exists so a
# trial can be told apart from a real payment when reading the log.
TRIAL_PLAN_KEY = "trial"


def is_subscribed(account):
    """
    Return True if the account has an active subscription.

    Superuser and bot accounts always return True.
    """
    if _is_exempt(account):
        return True

    expiry = account.subscription_expires_date
    if expiry is None:
        return False

    return datetime.now(timezone.utc) < expiry


def get_subscription_status(account):
    """
    Return a dict with subscription status info for display.

    Keys:
        subscribed (bool): Currently subscribed
        expiry (datetime|None): Expiry datetime (UTC)
        hours_remaining (float|None): Hours until expiry
        is_warning (bool): True if < 48h remaining
        is_exempt (bool): True if superuser/bot
    """
    if _is_exempt(account):
        return {
            "subscribed": True,
            "expiry": None,
            "hours_remaining": None,
            "is_warning": False,
            "is_exempt": True,
        }

    expiry = account.subscription_expires_date
    if expiry is None:
        return {
            "subscribed": False,
            "expiry": None,
            "hours_remaining": None,
            "is_warning": False,
            "is_exempt": False,
        }

    now = datetime.now(timezone.utc)
    if now >= expiry:
        return {
            "subscribed": False,
            "expiry": expiry,
            "hours_remaining": 0,
            "is_warning": False,
            "is_exempt": False,
        }

    remaining = expiry - now
    hours = remaining.total_seconds() / 3600
    return {
        "subscribed": True,
        "expiry": expiry,
        "hours_remaining": hours,
        "is_warning": hours < 48,
        "is_exempt": False,
    }


def extend_subscription(account, days):
    """
    Extend the account's subscription by the given number of days.

    If already subscribed, extends from current expiry (not from now).
    If expired or never subscribed, extends from now.

    Returns the new expiry datetime.
    """
    now = datetime.now(timezone.utc)
    current_expiry = account.subscription_expires_date

    if current_expiry and current_expiry > now:
        new_expiry = current_expiry + timedelta(days=days)
    else:
        new_expiry = now + timedelta(days=days)

    account.subscription_expires_date = new_expiry
    return new_expiry


def _trial_tx_hash(wallet_address):
    """The synthetic tx_hash a trial row carries.

    A trial has no on-chain transaction, but tx_hash is unique — so
    deriving it from the wallet makes one-trial-per-wallet a database
    constraint rather than a check that can be raced or bypassed.
    """
    return f"{TRIAL_PLAN_KEY}:{wallet_address}"


def has_had_trial(wallet_address):
    """Whether this wallet has ever been granted a trial.

    Asked of the wallet rather than the account, because the account is
    what a world rebuild destroys and the wallet is what identifies the
    player across one.
    """
    if not wallet_address:
        return False

    from subscriptions.models import SubscriptionPayment

    return (
        SubscriptionPayment.objects.using("subscriptions")
        .filter(tx_hash=_trial_tx_hash(wallet_address))
        .exists()
    )


def _record_trial(account, wallet_address, expiry):
    """Write the trial to the payment log so it outlives the account.

    This row is what makes a trial durable. The expiry also lives on the
    account as an attribute, but that is destroyed by the world rebuild
    this exists to survive; the subscriptions database is not.

    Skipped when there is no wallet. tx_hash is unique, so a second
    walletless trial would collide on "trial:None" and raise — and a
    trial nobody can key on is worth less than the account creation it
    would break.
    """
    if not wallet_address:
        return

    from subscriptions.models import SubscriptionPayment

    SubscriptionPayment.objects.using("subscriptions").create(
        # account_id and account_name are a point-in-time snapshot for
        # support, never a lookup key — both are re-issued or renamed by
        # a rebuild. Every query in this module keys on the wallet.
        account_id=account.id,
        account_name=account.key,
        wallet_address=wallet_address,
        plan_key=TRIAL_PLAN_KEY,
        amount=0,
        currency_code="",
        tx_hash=_trial_tx_hash(wallet_address),
        old_expiry=None,
        new_expiry=expiry,
    )


def grant_trial(account):
    """
    Grant the free trial period to a new account.

    Only grants if SUBSCRIPTION_TRIAL_HOURS > 0, the account has no
    existing subscription expiry set, and the wallet has never had a
    trial before.

    Returns the trial expiry datetime, or None if not granted.
    """
    if not getattr(settings, "SUBSCRIPTION_ENABLED", False):
        return None

    trial_hours = getattr(settings, "SUBSCRIPTION_TRIAL_HOURS", 48)
    if trial_hours <= 0:
        return None

    if account.subscription_expires_date is not None:
        return None

    wallet_address = account.wallet_address
    if has_had_trial(wallet_address):
        return None

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=trial_hours)
    account.subscription_expires_date = expiry
    _record_trial(account, wallet_address, expiry)
    return expiry


def has_paid(account):
    """
    Return True if the account has ever made a subscription payment.

    Free-trial-only accounts return False — trial rows are written to the
    same log, and are excluded here. Exempt accounts (superuser/bot)
    return True.

    Keyed on the wallet rather than the account id. A world rebuild
    re-issues every primary key, so an account_id lookup would report a
    player who has paid for a year as never having paid, and silently
    close export to them.
    """
    if _is_exempt(account):
        return True

    wallet_address = account.wallet_address
    if not wallet_address:
        return False

    from subscriptions.models import SubscriptionPayment

    return (
        SubscriptionPayment.objects.using("subscriptions")
        .filter(wallet_address=wallet_address)
        .exclude(plan_key=TRIAL_PLAN_KEY)
        .exists()
    )


def _is_exempt(account):
    """Check if account bypasses subscription (superuser or bot)."""
    if not getattr(settings, "SUBSCRIPTION_ENABLED", False):
        return True

    if getattr(settings, "SUBSCRIPTION_BYPASS_SUPERUSER", True):
        if account.is_superuser:
            return True

    bot_names = getattr(settings, "BOT_ACCOUNT_USERNAMES", [])
    if account.key in bot_names:
        return True

    return False

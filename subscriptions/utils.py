"""
Subscription status utilities.

Every subscription check in the codebase goes through this module.
"""

from datetime import datetime, timedelta, timezone

from django.conf import settings


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


def grant_trial(account):
    """
    Grant the free trial period to a new account.

    Only grants if SUBSCRIPTION_TRIAL_HOURS > 0 and account has no
    existing subscription expiry set.

    Returns the trial expiry datetime, or None if not granted.
    """
    if not getattr(settings, "SUBSCRIPTION_ENABLED", False):
        return None

    trial_hours = getattr(settings, "SUBSCRIPTION_TRIAL_HOURS", 48)
    if trial_hours <= 0:
        return None

    if account.subscription_expires_date is not None:
        return None

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=trial_hours)
    account.subscription_expires_date = expiry
    return expiry


def has_paid(account):
    """
    Return True if the account has ever made a subscription payment.

    Free-trial-only accounts return False. Exempt accounts (superuser/bot)
    return True.
    """
    if _is_exempt(account):
        return True

    from subscriptions.models import SubscriptionPayment

    return SubscriptionPayment.objects.using("subscriptions").filter(
        account_id=account.id
    ).exists()


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

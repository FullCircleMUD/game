"""
Subscribe command — pay for a game subscription via XRPL wallet.

Account-level (OOC) command. Creates a Xaman Payment payload for
RLUSD sent to the issuer wallet.

All XRPL/Xaman calls run in worker threads (deferToThread) so the
reactor stays responsive for other players.
"""

from django.conf import settings
from evennia import Command
from evennia.utils import delay
from evennia.utils.evmenu import get_input
from twisted.internet import threads

MAX_POLL_ATTEMPTS = 60  # 2 seconds × 60 = 2-minute timeout


class CmdSubscribe(Command):
    """
    Subscribe or extend your game subscription.

    Usage:
        subscribe

    Shows available subscription plans. Select one to pay via
    your Xaman wallet.
    """

    key = "subscribe"
    aliases = ["sub"]
    locks = "cmd:is_ooc()"
    help_category = "System"

    def func(self):
        if not getattr(settings, "SUBSCRIPTION_ENABLED", False):
            self.caller.msg("Subscriptions are not currently active. Enjoy free access!")
            return

        account = self.caller

        wallet = account.wallet_address
        if not wallet:
            account.msg("|rNo wallet linked to your account.|n")
            return

        from subscriptions.utils import get_subscription_status

        status = get_subscription_status(account)
        if status["is_exempt"]:
            account.msg("Your account does not require a subscription.")
            return

        if status["subscribed"]:
            expiry = status["expiry"]
            account.msg(
                f"|cYou are subscribed until "
                f"{expiry.strftime('%H:%M UTC on %d %B %Y')}.|n"
            )
            account.msg(
                "You can extend your subscription by purchasing "
                "another period.\n"
            )
        else:
            account.msg("|rYou are not currently subscribed.|n\n")

        # Fetch available plans from DB
        from subscriptions.models import SubscriptionPlan

        plans = list(
            SubscriptionPlan.objects.using("subscriptions").filter(
                is_active=True
            )
        )
        if not plans:
            account.msg("|rNo subscription plans are currently available.|n")
            return

        currency = settings.SUBSCRIPTION_CURRENCY_CODE

        lines = ["|c--- Subscription Plans ---|n"]
        for i, plan in enumerate(plans, 1):
            lines.append(
                f"  {i}. {plan.display_name} — "
                f"{plan.price} {currency} ({plan.duration_days} days)"
            )
        lines.append("")
        lines.append("Select a plan number to subscribe:")
        account.msg("\n".join(lines))

        # Store plans on ndb for the callback
        account.ndb._subscription_plans = plans

        get_input(
            account,
            "\nPlan number (or 'cancel'): ",
            _on_plan_selected,
        )


def _on_plan_selected(account, prompt, result):
    """get_input callback — user selected a plan."""
    plans = getattr(account.ndb, "_subscription_plans", None)
    if not plans:
        account.msg("No plans available.")
        return False

    answer = result.strip().lower()
    if answer in ("cancel", "c", "no", "n", ""):
        account.msg("Subscription cancelled.")
        if hasattr(account.ndb, "_subscription_plans"):
            del account.ndb._subscription_plans
        return False

    try:
        selection = int(answer)
    except ValueError:
        account.msg("Enter a number or 'cancel'.")
        return False

    if selection < 1 or selection > len(plans):
        account.msg(f"Invalid selection. Choose 1-{len(plans)} or 'cancel'.")
        return False

    plan = plans[selection - 1]
    if hasattr(account.ndb, "_subscription_plans"):
        del account.ndb._subscription_plans

    currency_code = settings.SUBSCRIPTION_CURRENCY_CODE
    currency_issuer = settings.SUBSCRIPTION_CURRENCY_ISSUER
    destination = settings.SUBSCRIPTION_PAYMENT_DESTINATION

    if not currency_issuer:
        account.msg(
            "|rSubscription payment currency issuer is not configured. "
            "Contact an admin.|n"
        )
        return False

    get_input(
        account,
        f"\n|c--- Subscribe: {plan.display_name} ---|n"
        f"\nPay |w{plan.price} {currency_code}|n "
        f"for {plan.duration_days} days?"
        f"\nThis requires signing one transaction in Xaman."
        f"\n\n[Y]/N? ",
        lambda caller, prompt2, result2: _on_subscribe_confirmed(
            caller,
            plan,
            currency_code,
            currency_issuer,
            destination,
            result2,
        ),
    )
    return False


def _on_subscribe_confirmed(
    account, plan, currency_code, currency_issuer, destination, answer
):
    """get_input callback — user confirmed subscription purchase."""
    if answer.strip().lower() in ("n", "no"):
        account.msg("Subscription cancelled.")
        return False

    from blockchain.xrpl.xrpl_tx import encode_currency_hex
    from blockchain.xrpl.memo import build_memo, MEMO_SUBSCRIBE

    hex_code = encode_currency_hex(currency_code)
    memos = [build_memo(MEMO_SUBSCRIBE, {
        "plan": plan.display_name, "amount": str(plan.price),
        "currency": currency_code,
    })]

    account.msg("|cCreating payment request...|n")
    d = threads.deferToThread(
        _create_subscription_payload,
        destination,
        hex_code,
        plan.price,
        currency_issuer,
        memos,
    )
    d.addCallback(
        lambda payload: _on_payment_payload(
            account,
            plan,
            currency_code,
            currency_issuer,
            destination,
            hex_code,
            payload,
        )
    )
    d.addErrback(
        lambda f: _msg(
            account,
            f"|rError contacting Xaman: {f.getErrorMessage()}|n",
        )
    )
    return False


def _on_payment_payload(
    account, plan, currency_code, currency_issuer, destination, hex_code,
    payload,
):
    """Reactor thread — show deeplink and start polling."""
    if not _connected(account):
        return

    uuid = payload["uuid"]
    deeplink = payload["deeplink"]

    account.msg("|c--- Sign Payment ---|n")
    account.msg(f"\nOpen this link to sign in Xaman:")
    account.msg(f"|w{deeplink}|n")
    account.msg(f"\nWaiting for you to sign... (2 minute timeout)")

    _poll_subscription_payment(
        account,
        plan,
        currency_code,
        currency_issuer,
        destination,
        hex_code,
        uuid,
        attempt=0,
    )


def _poll_subscription_payment(
    account, plan, currency_code, currency_issuer, destination, hex_code,
    uuid, attempt,
):
    """Poll Xaman for subscription payment signing result."""
    if not _connected(account):
        return

    if attempt >= MAX_POLL_ATTEMPTS:
        _msg(account, "|r--- Timed out waiting for Xaman signing ---|n")
        return

    d = threads.deferToThread(_get_payload_status, uuid)
    d.addCallback(
        lambda status: _on_poll_result(
            account,
            plan,
            currency_code,
            currency_issuer,
            destination,
            hex_code,
            uuid,
            attempt,
            status,
        )
    )
    d.addErrback(
        lambda f: _msg(
            account,
            f"|rError polling Xaman: {f.getErrorMessage()}|n",
        )
    )


def _on_poll_result(
    account, plan, currency_code, currency_issuer, destination, hex_code,
    uuid, attempt, status,
):
    """Reactor thread — process subscription payment poll result."""
    if not _connected(account):
        return

    if status["expired"]:
        _msg(account, "|r--- Xaman request expired ---|n")
        return

    if not status["resolved"]:
        delay(
            2,
            _poll_subscription_payment,
            account,
            plan,
            currency_code,
            currency_issuer,
            destination,
            hex_code,
            uuid,
            attempt + 1,
        )
        return

    if not status["signed"]:
        _msg(account, "|r--- Payment was rejected ---|n")
        return

    tx_hash = status.get("tx_hash")

    # Verify on-chain in worker thread
    account.msg("|cVerifying on-chain payment...|n")
    d = threads.deferToThread(
        _verify_subscription_payment,
        tx_hash,
        destination,
        hex_code,
        plan.price,
        currency_issuer,
    )
    d.addCallback(
        lambda verified_amount: _on_payment_verified(
            account, plan, currency_code, tx_hash, verified_amount,
        )
    )
    d.addErrback(lambda f: _on_verify_error(account, f, tx_hash))


def _on_payment_verified(account, plan, currency_code, tx_hash,
                         verified_amount):
    """Reactor thread — payment verified, extend subscription."""
    if not _connected(account):
        return

    from subscriptions.models import SubscriptionPayment
    from subscriptions.utils import extend_subscription

    old_expiry = account.subscription_expires_date
    new_expiry = extend_subscription(account, plan.duration_days)

    # Record payment in subscriptions DB
    try:
        SubscriptionPayment.objects.using("subscriptions").create(
            account_id=account.id,
            account_name=account.key,
            wallet_address=account.wallet_address,
            plan_key=plan.key,
            amount=plan.price,
            currency_code=currency_code,
            tx_hash=tx_hash,
            old_expiry=old_expiry,
            new_expiry=new_expiry,
        )
    except Exception as e:
        # Payment verified on-chain but DB record failed.
        # Subscription was already extended — log for admin.
        import logging

        logging.getLogger("evennia").error(
            f"Subscription payment DB record failed: {e} "
            f"(account={account.key}, tx={tx_hash})"
        )

    expiry_str = new_expiry.strftime("%H:%M UTC on %d %B %Y")
    account.msg(
        f"\n|g--- Subscription Active ---|n"
        f"\nYour subscription is now active until {expiry_str}."
        f"\nTx: |w{tx_hash}|n\n"
    )

    # Refresh the OOC menu
    account.msg(account.at_look(session=None))


def _on_verify_error(account, failure, tx_hash):
    """Reactor thread — on-chain verification failed."""
    if not _connected(account):
        return
    account.msg("|r--- On-chain verification failed ---|n")
    account.msg(f"|r{failure.getErrorMessage()}|n")
    account.msg(f"|yTx hash: {tx_hash} — contact an admin.|n")


# ================================================================== #
#  Worker thread helpers (no Evennia object access)
# ================================================================== #


def _create_subscription_payload(destination, hex_code, amount, issuer,
                                 memos=None):
    """Worker thread — create Xaman payment payload."""
    from blockchain.xrpl.xaman import create_payment_payload

    return create_payment_payload(destination, hex_code, amount, issuer,
                                  memos=memos)


def _get_payload_status(uuid):
    """Worker thread — poll Xaman API."""
    from blockchain.xrpl.xaman import get_payload_status

    return get_payload_status(uuid)


def _verify_subscription_payment(
    tx_hash, destination, hex_code, amount, issuer
):
    """Worker thread — verify on-chain payment."""
    from blockchain.xrpl.xrpl_tx import verify_fungible_payment

    return verify_fungible_payment(
        tx_hash,
        expected_destination=destination,
        expected_currency_hex=hex_code,
        expected_amount=amount,
        expected_issuer=issuer,
    )


# ================================================================== #
#  Shared helpers
# ================================================================== #


def _connected(account):
    """True if the account still has an active session."""
    return account.sessions.count() > 0


def _msg(account, text):
    """Send a message only if the account is still connected."""
    if _connected(account):
        account.msg(text)

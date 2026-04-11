"""
Connect to the game via Xaman wallet sign-in or password (root/bot).

If the wallet has no account, the player is prompted for a username
and an account is created automatically.

Usage (at login screen):
    connect                       — wallet sign-in via Xaman
    connect root <password>       — root login
    connect <bot_name> <password> — bot login
"""

import re
from django.conf import settings
from evennia.utils import class_from_module, utils, delay
from twisted.internet import threads
from evennia.accounts.models import AccountDB

COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)

MAX_POLL_ATTEMPTS = 60  # 2 seconds * 60 = 2 minute timeout


class CmdUnconnectedConnect(COMMAND_DEFAULT_CLASS):
    """
    Connect to the game.

    Usage (at login screen):
      connect                — sign in with your Xaman wallet
      connect root <password> — root/admin login

    If your wallet is not linked to an account, you will be prompted
    to choose a username and an account will be created for you.
    """

    key = "connect"
    aliases = ["conn", "con", "co"]
    locks = "cmd:all()"
    arg_regex = r"\s.*?|$"

    def func(self):
        session = self.caller
        address = session.address
        args = self.args.strip()

        # ── Password-based login (root / bot) ──────────────────────
        if args:
            parts = [part.strip() for part in re.split(r"\"", args) if part.strip()]
            if len(parts) == 1:
                parts = parts[0].split(None, 1)

            bot_enabled = getattr(settings, "BOT_LOGIN_ENABLED", False)
            bot_usernames = getattr(settings, "BOT_ACCOUNT_USERNAMES", [])
            superuser_name = getattr(settings, "EVENNIA_SUPERUSER_USERNAME", "root")
            is_root = len(parts) == 2 and parts[0].lower() == superuser_name.lower()
            is_bot = (
                bot_enabled
                and len(parts) == 2
                and parts[0].lower() in [u.lower() for u in bot_usernames]
            )

            if is_root or is_bot:
                Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
                name, password = parts
                account, errors = Account.authenticate(
                    username=name, password=password, ip=address, session=session
                )
                if account:
                    session.sessionhandler.login(session, account)
                else:
                    session.msg("|R%s|n" % "\n".join(errors))
                return

        # ── Xaman wallet sign-in ──────────────────────────────────
        answer = yield (
            f"\n\n|cSign in with your Xaman wallet|n"
            "\nThis is a signature only, no on-chain transaction will be performed."
            "\n\nDo you wish to proceed? [Y]/N?"
        )
        if answer.lower() in ("n", "no"):
            session.msg("\n|cAborted.|n")
            return

        from blockchain.xrpl.xaman import create_signin_payload

        session.msg("|cContacting Xaman...|n")
        d = threads.deferToThread(create_signin_payload)
        d.addCallback(lambda payload: _on_signin_payload(session, address, payload))
        d.addErrback(lambda f: session.msg(f"|rError contacting Xaman: {f.getErrorMessage()}|n"))


def _on_signin_payload(session, address, payload):
    """Reactor thread — Xaman payload created, show deeplink and start polling."""
    uuid = payload["uuid"]
    deeplink = payload["deeplink"]

    session.msg("|c--- Sign in with your Xaman wallet ---|n")
    session.msg(f"\nOpen this link in your browser or tap on mobile:")
    session.msg(f"|w{deeplink}|n")
    session.msg(f"\nWaiting for you to sign... (2 minute timeout)")

    session.ndb.xaman_uuid = uuid
    session.ndb.xaman_action = "connect"

    _poll_xaman(session, uuid, address, attempt=0)


def _poll_xaman(session, uuid, address, attempt):
    """Schedule a non-blocking poll of Xaman API."""
    from blockchain.xrpl.xaman import get_payload_status

    if attempt >= MAX_POLL_ATTEMPTS:
        session.msg("|r--- Timed out waiting for Xaman sign-in ---|n")
        session.msg("|r--- Aborted ---|n")
        _clear_xaman_state(session)
        return

    d = threads.deferToThread(get_payload_status, uuid)
    d.addCallback(lambda status: _on_poll_result(session, uuid, address, attempt, status))
    d.addErrback(lambda f: _on_poll_error(session, f))


def _on_poll_error(session, failure):
    """Reactor thread — Xaman poll failed."""
    session.msg(f"|rError polling Xaman: {failure.getErrorMessage()}|n")
    session.msg("|r--- Aborted ---|n")
    _clear_xaman_state(session)


def _on_poll_result(session, uuid, address, attempt, status):
    """Reactor thread — process Xaman poll result."""
    if status["expired"]:
        session.msg("|r--- Xaman request expired ---|n")
        session.msg("|r--- Aborted ---|n")
        _clear_xaman_state(session)
        return

    if not status["resolved"]:
        delay(2, _poll_xaman, session, uuid, address, attempt + 1)
        return

    if not status["signed"]:
        session.msg("|r--- Sign-in was rejected ---|n")
        session.msg("|r--- Aborted ---|n")
        _clear_xaman_state(session)
        return

    wallet_address = status["wallet_address"]

    if not wallet_address:
        session.msg("|r--- No wallet address returned ---|n")
        session.msg("|r--- Aborted ---|n")
        _clear_xaman_state(session)
        return

    session.msg("|g--- Wallet verified successfully! ---|n")

    # ── Look up existing account by wallet ─────────────────────
    existing = AccountDB.objects.get_by_attribute(
        key="wallet_address", value=wallet_address
    )

    if existing.exists():
        # Account found — authenticate and login
        acct = existing.first()
        Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

        acct_auth, errors = Account.authenticate(
            username=acct.key,
            password=settings.DEFAULT_ACCOUNT_PASSWORD,
            ip=address,
            session=session,
        )

        if acct_auth:
            session.sessionhandler.login(session, acct_auth)
        else:
            session.msg("|R%s|n" % "\n".join(errors))

        _clear_xaman_state(session)
        return

    # ── No account — create one ────────────────────────────────
    if not getattr(settings, "NEW_ACCOUNT_REGISTRATION_ENABLED", True):
        session.msg("|rRegistration is currently disabled.|n")
        _clear_xaman_state(session)
        return

    session.msg("\n|gNo account found for this wallet — let's create one!|n")

    # Store wallet address and IP on session for the username callback
    session.ndb.xaman_wallet_address = wallet_address
    session.ndb.xaman_address = address

    from evennia.utils.evmenu import get_input
    from django.conf import settings as django_settings

    website_url = getattr(django_settings, 'GAME_WEBSITE_URL', 'https://fcmud.world')
    tos_prompt = (
        "\n|c--- Terms of Service ---|n"
        "\nBefore creating an account you must agree to the Terms of Service."
        f"\n\nRead the full Terms of Service at:"
        f"\n|w{website_url}/terms/|n"
        "\n\nBy creating an account you agree to be bound by these terms,"
        "\nincluding the jurisdictional restrictions on the gold redemption feature."
        "\n\nDo you agree to the Terms of Service? Y/[N]: "
    )
    get_input(session, tos_prompt, _handle_tos_acceptance)


def _handle_tos_acceptance(caller, prompt, result):
    """
    Callback for get_input() — handles Terms of Service acceptance.

    Defaults to No if the player just presses Enter without typing Y.
    Returns False to finish the prompt chain (success or decline).
    """
    session = caller
    if result.strip().lower() not in ('y', 'yes'):
        session.msg(
            "\n|rAccount creation cancelled.|n"
            "\nYou must agree to the Terms of Service to create an account."
            "\nType |wconnect|n again if you change your mind."
        )
        _clear_xaman_state(session)
        return False

    # ToS accepted — record on session and proceed to username selection
    session.ndb.tos_accepted = True

    # Use delay(0) to schedule the next get_input on the next reactor tick.
    # Chaining get_input directly inside a get_input callback causes the outer
    # cleanup (InputCmdSet removal) to destroy the newly-added InputCmdSet.
    from evennia.utils import delay
    delay(0, _start_username_prompt, session)
    return False


def _start_username_prompt(session):
    """Reactor-tick-deferred entry point for the username prompt."""
    from evennia.utils.evmenu import get_input
    get_input(session, "\nChoose a username: ", _handle_username_input)


def _handle_username_input(caller, prompt, result):
    """
    Callback for get_input() — validates username and creates account.

    Returns True to re-prompt (invalid/taken name), False to finish.
    """
    session = caller
    username = result.strip()
    wallet_address = session.ndb.xaman_wallet_address
    address = session.ndb.xaman_address

    if not username:
        session.msg("|rUsername cannot be empty.|n")
        return True

    Account = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)

    # Normalize
    original = username
    username = Account.normalize_username(username)
    if original != username:
        session.msg(
            "Note: your username was normalized to strip spaces and remove "
            "characters that could be visually confusing."
        )

    # Validate format
    valid, errs = Account.validate_username(username)
    if not valid:
        session.msg("|R%s|n" % "\n".join(errs))
        return True

    # Duplicate name check
    if AccountDB.objects.filter(username__iexact=username).exists():
        session.msg("|rSorry, that username is already taken.|n")
        return True

    # Create the account
    try:
        account, errors = Account.create(
            username=username,
            password=settings.DEFAULT_ACCOUNT_PASSWORD,
            wallet_address=wallet_address,
            ip=address,
            session=session,
        )

        if account:
            from datetime import datetime, timezone
            account.db.tos_agreed_at = datetime.now(timezone.utc).isoformat()
            account.db.tos_version = getattr(settings, 'TOS_VERSION', 'unknown')
            session.sessionhandler.login(session, account)
        else:
            session.msg("|R%s|n" % "\n".join(errors))

    except Exception as e:
        session.msg(f"|r--- Account Creation Error: {e} ---|n")

    _clear_xaman_state(session)
    return False


def _clear_xaman_state(session):
    """Clear temporary Xaman polling state from session."""
    session.ndb.xaman_uuid = None
    session.ndb.xaman_action = None
    session.ndb.xaman_wallet_address = None
    session.ndb.xaman_address = None

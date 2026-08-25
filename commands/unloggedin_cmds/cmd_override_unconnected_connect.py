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
from contextlib import contextmanager

from django.conf import settings
from evennia.utils import class_from_module, utils, delay, logger
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
    aliases = ["con"]
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
        _login_account(session, address, existing.first())
        _clear_xaman_state(session)
        return

    # ── No live account — check the archive before creating one ──
    #
    # Order matters. Creating an account first takes the username and
    # mints a fresh archive identity, which leaves any archived account
    # for this wallet unrestorable.
    session.msg("|cNo active account for this wallet.|n")
    session.msg("|cChecking whether your account has been archived...|n")

    d = threads.deferToThread(_find_archived_account, wallet_address)
    d.addCallback(lambda ids: _on_archive_lookup(session, address, wallet_address, ids))
    d.addErrback(lambda f: _on_archive_error(session, f))


def _login_account(session, address, acct):
    """Reactor thread — authenticate a known account and log it in."""
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


def _find_archived_account(wallet_address):
    """Worker thread — search the archive for an account with this wallet.

    Deferred because neither Attribute value column is indexed and
    wallet_address is stored pickled, so this is a table scan that would
    otherwise block every connected player.
    """
    from evennia_archive.api import find

    return find("wallet_address", wallet_address, model="accountdb")


def _on_archive_lookup(session, address, wallet_address, archive_ids):
    """Reactor thread — the archive has been searched."""
    if not archive_ids:
        session.msg("|cNo archived account found.|n")
        _begin_account_creation(session, address, wallet_address)
        return

    if len(archive_ids) > 1:
        # A wallet identifies one account, so more than one hit means
        # something upstream is wrong. Visible in the log, not to the
        # player, who should not be blocked by it.
        logger.log_err(
            f"Multiple archived accounts for wallet {wallet_address}: {archive_ids}"
        )

    session.msg("|gArchived account found — restoring your account...|n")

    d = threads.deferToThread(_restore_account, archive_ids[0])
    d.addCallback(lambda acct: _on_account_restored(session, address, acct))
    d.addErrback(lambda f: _on_archive_error(session, f))


def _restore_account(archive_id):
    """Worker thread — rebuild the archived account in the live database."""
    from evennia_archive.api import restore

    return restore(archive_id)


def _on_account_restored(session, address, acct):
    """Reactor thread — the account is back; now recover what it holds."""
    session.msg(f"|gAccount |w{acct.key}|n|g restored.|n")
    session.msg("|cRecovering your bank...|n")

    d = threads.deferToThread(_restore_bank, acct)
    d.addCallback(lambda count: _on_bank_restored(session, address, acct, count))
    d.addErrback(lambda f: _on_bank_restore_error(session, address, acct, f))


def _restore_bank(acct):
    """Worker thread — rebuild the account's banked items.

    The ownership mirror survives a world rebuild untouched, so it still
    knows every item this wallet had banked. What it lost is the Evennia
    object for each one. This puts those back and writes nothing: the
    mirror already says ACCOUNT, which is where they are going.

    Keyed on the wallet alone. Banked items carry no character_key, so
    this half of the recovery is immune to the character-name questions
    that the inventory half has to care about.

    Returns the number of items rebuilt.
    """
    from blockchain.xrpl.models import FungibleGameState
    from blockchain.xrpl.services.nft import NFTService
    from commands.room_specific_cmds.bank.cmd_balance import ensure_bank

    wallet = acct.wallet_address
    if not wallet:
        return 0

    # The account's db.bank is a dbref into the database that was
    # rebuilt, so it dereferences to None and a fresh bank is made here.
    # at_post_login would do the same later; doing it now means there is
    # somewhere to put the items.
    bank = ensure_bank(acct)

    # Banked items are stamped "*" — global, like the bank itself — so
    # they are reachable from whichever shard the account is playing on.
    recovered = _restore_items(
        NFTService.get_account_nfts(wallet), bank, _global_shard(),
    )
    _restore_balances(bank, wallet, FungibleGameState.LOCATION_ACCOUNT)

    return recovered


def _global_shard():
    """The "*" sentinel, or None in monolith."""
    from evennia_shards import GLOBAL_SHARD_ID, ROLE_MONOLITH, get_role

    if get_role() == ROLE_MONOLITH:
        return None
    return GLOBAL_SHARD_ID


@contextmanager
def _stamping_as(shard_id):
    """Insert rows stamped with this shard, or unscoped in monolith.

    A no-op when shard_id is None, which is monolith — the shards
    tenancy is not installed there, ObjectDB has no shard_id column, and
    entering a context would fail rather than help.
    """
    if shard_id is None:
        yield
        return

    from evennia_shards import shard_context

    with shard_context(shard_id):
        yield


def _recovery_shard(obj):
    """The shard a recovered object should be stamped with.

    None in monolith, where nothing is stamped at all.
    """
    from evennia_shards import ROLE_MONOLITH, get_role

    if get_role() == ROLE_MONOLITH:
        return None
    return getattr(obj, "shard_id", None)


def _restore_items(rows, container, shard_id):
    """Rebuild each ownership row's game object into container.

    Shared by the bank and the character halves — they differ only in
    which rows come in, where they go, and what the items are stamped
    with.

    ``recovering=True`` is what stops the mirror booking each rebuild as
    an arrival; see NFTMirrorMixin._handle_creation.

    ``shard_id`` is given rather than inferred. Recovery runs on the
    router, which is unscoped, and inside a worker thread, which carries
    no tenant context of its own — so an insert here lands shard_id NULL
    and the shards guard refuses it. Entering a shard's context around
    the insert is what the library does for router-side chargen.

    Banked items are stamped ``"*"``, so they are reachable from every
    shard, as the bank itself is. A character's items take that
    character's shard. Pass None in monolith, where the column does not
    exist.

    Returns the number rebuilt.
    """
    from typeclasses.items.base_nft_item import BaseNFTItem

    recovered = 0
    for row in rows:
        with _stamping_as(shard_id):
            obj = BaseNFTItem.spawn_into(
                row.nftoken_id, container, recovering=True,
            )
        if obj is None:
            logger.log_err(
                f"Could not rebuild item {row.nftoken_id} into {container}"
            )
            continue
        # Recovery runs on the router, which is not meant to hold game
        # objects. The row stays; only the instance is evicted.
        obj.flush_from_cache(force=True)
        recovered += 1

    return recovered


def _restore_balances(holder, wallet, location, character_key=None):
    """Write gold and resources onto a bank or a character.

    The mirror is the source of truth and survives the rebuild, so this
    is a straight assignment from mirror to holder, not a reconciliation.
    Whatever the holder had is overwritten.

    That matters most for characters. The archive is written at seams —
    logout, a level, a training — while the mirror is written as the
    player plays. So a character restored from the archive carries the
    balance it had at its last seam, and the mirror carries what it had
    when the world went down. Taking the mirror gives them back what they
    actually held.

    Set directly rather than through the mixin's deposit methods, which
    would each write the amount back into the mirror as a fresh banking
    of gold that is already banked.

    Gold is matched on the configured currency code rather than inferred
    from a null resource_id. Proxy tokens — the ``P``-prefixed currencies
    behind AMM shop pricing — also have no resource id, and crediting one
    as gold would hand the player currency that does not exist in game.

    Amounts are whole units. The column allows six decimal places for
    ledger compatibility, but nothing in the game trades fractions of a
    gold piece or a sack of flour.
    """
    from blockchain.xrpl import currency_cache
    from blockchain.xrpl.services.fungible import FungibleService

    gold = 0
    resources = {}

    rows = FungibleService.get_all_balances(
        None, wallet, location, character_key=character_key,
    )
    for row in rows:
        if row.currency_code == settings.XRPL_GOLD_CURRENCY_CODE:
            gold = int(row.balance)
            continue

        resource_id = currency_cache.get_resource_id(row.currency_code)
        if resource_id is None:
            # A proxy token, or a currency with no in-game resource. A
            # proxy token in a player position should not happen at all —
            # they exist only to price NFT items against an AMM — so this
            # is worth seeing rather than silently crediting or dropping.
            # The mirror keeps the row either way.
            logger.log_err(
                f"Recovery: {row.currency_code} has no in-game resource "
                f"({wallet}, {location}); not credited. A P-prefixed "
                "proxy token here means something upstream mis-booked it."
            )
            continue

        resources[resource_id] = int(row.balance)

    holder.db.gold = gold
    holder.db.resources = resources


def _on_bank_restored(session, address, acct, count):
    """Reactor thread — bank done, move on to the characters."""
    if count:
        session.msg(f"|gRecovered {count} banked item(s).|n")

    session.msg("|cLooking for your characters...|n")

    d = threads.deferToThread(_restore_characters, acct)
    d.addCallback(lambda chars: _on_characters_restored(session, address, acct, chars))
    d.addErrback(lambda f: _on_character_restore_error(session, address, acct, f))


def _on_bank_restore_error(session, address, acct, failure):
    """Reactor thread — the bank could not be rebuilt; carry on regardless.

    The ownership record is untouched — it is the source of truth and
    this only ever read it — so nothing is lost, and a later sign-in can
    try again. Stopping here would cost them their characters too, for a
    fault that did not touch them.
    """
    logger.log_err(f"Bank recovery failed for {acct}: {failure.getTraceback()}")
    session.msg(
        "|yYour banked items could not be recovered just now. Your "
        "ownership records are intact — please try signing in again "
        "shortly.|n"
    )

    session.msg("|cLooking for your characters...|n")

    d = threads.deferToThread(_restore_characters, acct)
    d.addCallback(lambda chars: _on_characters_restored(session, address, acct, chars))
    d.addErrback(lambda f: _on_character_restore_error(session, address, acct, f))


def _restore_characters(acct):
    """Worker thread — rebuild every character belonging to this wallet.

    Searched by ``account_wallet``, the copy of the owning wallet each
    character carries. The live link — ``db_account`` — is a foreign key,
    and restore() drops those; the account's ``_playable_characters`` is
    no better, being a list of dbrefs into the database that was rebuilt.
    The stamped wallet is the only thing that crosses the gap.

    Returns the restored characters. restore() is idempotent, so a
    character already live comes back as itself rather than a second copy.
    """
    from evennia_archive.api import find, restore

    wallet = acct.wallet_address
    if not wallet:
        return []

    restored = []
    for archive_id in find("account_wallet", wallet, model="objectdb"):
        char = restore(archive_id)
        _restore_character_assets(char, wallet)
        restored.append(char)

    return restored


def _restore_character_assets(char, wallet):
    """Give a restored character back its items and balances.

    Same shape as the bank, differing only in the filter and the holder.
    The mirror is read and never written in either case.

    Balances overwrite whatever the archive restored. The archived figure
    is from the character's last seam; the mirror's is from when the world
    went down, which is the later of the two and the one they actually
    had.
    """
    from blockchain.xrpl.models import FungibleGameState
    from blockchain.xrpl.services.nft import NFTService

    # A character's items take that character's own shard. The character
    # was restored carrying its shard_id, because that is a column on
    # ObjectDB and the archive copies it across.
    _restore_items(
        NFTService.get_character_nfts(wallet, char.key),
        char,
        _recovery_shard(char),
    )
    _restore_balances(
        char,
        wallet,
        FungibleGameState.LOCATION_CHARACTER,
        character_key=char.key,
    )


def _on_characters_restored(session, address, acct, characters):
    """Reactor thread — reattach the characters and log in."""
    for char in characters:
        try:
            _reattach_character(acct, char)
        except Exception:
            logger.log_err(
                f"Failed to reattach restored character {char} to {acct}"
            )
            logger.log_trace()

    if characters:
        names = ", ".join(str(char.key) for char in characters)
        session.msg(f"|gRecovered {len(characters)} character(s): |w{names}|n")
    else:
        session.msg("|cNo archived characters found for this wallet.|n")

    # Recovery runs on the router, which is not meant to hold game
    # objects. The characters had to be instantiated to take their
    # balances and their account links, but this is the last use of them
    # — the rows stay, only the instances are evicted. Read the names
    # above first; a flushed instance is no longer worth reading from.
    for char in characters:
        char.flush_from_cache(force=True)

    _login_account(session, address, acct)
    _clear_xaman_state(session)


def _reattach_character(acct, char):
    """Put a restored character back under its account.

    Two links, because Evennia keeps two. ``db_account`` is the foreign
    key the game reads from the character's side; ``characters`` is the
    account-side list the OOC menu and `ic` are driven from. Restoring
    without both leaves a character that exists and cannot be played.

    Location and home are deliberately left alone — at_pre_puppet already
    repairs a character whose world was rebuilt underneath it, and it
    knows the fallback order (dungeon entrance, last rent, home, Limbo)
    far better than this code could.
    """
    char.db_account = acct
    char.save(update_fields=["db_account"])
    acct.characters.add(char)


def _on_character_restore_error(session, address, acct, failure):
    """Reactor thread — the account is back but its characters are not.

    Log them in regardless. The account is already live and usable, and
    blocking sign-in over a failed character search would cost them more
    than the missing characters do — the archive still holds them, so the
    next sign-in can try again.
    """
    logger.log_err(f"Character restore failed for {acct}: {failure.getTraceback()}")
    session.msg(
        "|yYour account was restored, but your characters could not be "
        "recovered just now. They are still archived — please try signing "
        "in again shortly.|n"
    )
    _login_account(session, address, acct)
    _clear_xaman_state(session)


def _on_archive_error(session, failure):
    """Reactor thread — the archive could not be consulted.

    Refuses rather than falling through to account creation. A new
    account would take the username and mint its own identity, making
    the archived one unrestorable — permanent damage from what may be a
    momentary fault. A retry costs the player nothing by comparison.
    """
    logger.log_err(f"Archive lookup failed: {failure.getTraceback()}")
    session.msg(
        "|rCould not reach the account archive. Your account may exist, "
        "and creating a new one now would make it unrecoverable.|n"
        "\n|rPlease try again shortly.|n"
    )
    _clear_xaman_state(session)


def _begin_account_creation(session, address, wallet_address):
    """Reactor thread — no account live or archived; start registration."""
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

    # Duplicate name check — live database first, then the archive.
    #
    # The archive half is what stops a newcomer taking the username of a
    # player who is away. After a world rebuild the live database holds
    # no accounts, so every name reads as free until its owner signs in;
    # by then it is gone, and restore() would hand them back their
    # account as "rowan1". Refusing the newcomer costs them a retry.
    #
    # Mirrors the character name check in chargen. Both query an indexed
    # column, so neither is the expensive attribute search find() does.
    #
    # This is what makes the library's restore-time rename unreachable in
    # the wallet flow. That rename stays where it is, as the library's own
    # backstop for accounts created by paths that never ran this check.
    taken = AccountDB.objects.filter(username__iexact=username).exists()
    if not taken:
        taken = (
            AccountDB.objects.using("archive")
            .filter(username__iexact=username)
            .exists()
        )
    if taken:
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

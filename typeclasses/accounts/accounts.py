"""
Typeclass for Account objects.

Note that this object is primarily intended to
store OOC information, not game info! This
object represents the actual user (not their
character) and has NO actual presence in the
game world (this is handled by the associated
character object, so you should customize that
instead for most things).

"""

# import broughtover ftom parent default account to 
# ensure overrdden methid have everything they need
# clean up when finished overidding methods
import re
import time
import typing
from random import getrandbits

from django.conf import settings
from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _

import evennia
from evennia.utils.create import create_object
from evennia.accounts.manager import AccountManager
from typeclasses.accounts.account_bank import AccountBank
from evennia.accounts.models import AccountDB
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.comms.models import ChannelDB
from evennia.objects.models import ObjectDB
from evennia.scripts.scripthandler import ScriptHandler
from evennia.server.models import ServerConfig
from evennia.server.signals import (
    SIGNAL_ACCOUNT_POST_CREATE,
    SIGNAL_ACCOUNT_POST_LOGIN_FAIL,
    SIGNAL_OBJECT_POST_PUPPET,
    SIGNAL_OBJECT_POST_UNPUPPET,
)
from evennia.server.throttle import Throttle
from evennia.typeclasses.attributes import ModelAttributeBackend, NickHandler
from evennia.typeclasses.models import TypeclassBase
from evennia.utils import class_from_module, create, logger
from evennia.utils.optionhandler import OptionHandler
from evennia.utils.utils import (
    is_iter,
    lazy_property,
    make_iter,
    to_str,
    variable_from_module,
)

__all__ = ("DefaultAccount", "DefaultGuest")

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit(".", 1))
_MULTISESSION_MODE = settings.MULTISESSION_MODE
_AUTO_CREATE_CHARACTER_WITH_ACCOUNT = settings.AUTO_CREATE_CHARACTER_WITH_ACCOUNT
_AUTO_PUPPET_ON_LOGIN = settings.AUTO_PUPPET_ON_LOGIN
_MAX_NR_SIMULTANEOUS_PUPPETS = settings.MAX_NR_SIMULTANEOUS_PUPPETS
_MAX_NR_CHARACTERS = settings.MAX_NR_CHARACTERS
_CMDSET_ACCOUNT = settings.CMDSET_ACCOUNT
_MUDINFO_CHANNEL = None
_CONNECT_CHANNEL = None
_CMDHANDLER = None


# Create throttles for too many account-creations and login attempts
CREATION_THROTTLE = Throttle(
    name="creation",
    limit=settings.CREATION_THROTTLE_LIMIT,
    timeout=settings.CREATION_THROTTLE_TIMEOUT,
)
LOGIN_THROTTLE = Throttle(
    name="login", limit=settings.LOGIN_THROTTLE_LIMIT, timeout=settings.LOGIN_THROTTLE_TIMEOUT
)



"""
Account

The Account represents the game "account" and each login has only one
Account object. An Account is what chats on default channels but has no
other in-game-world existence. Rather the Account puppets Objects (such
as Characters) in order to actually participate in the game world.


Guest

Guest accounts are simple low-level accounts that are created/deleted
on the fly and allows users to test the game without the commitment
of a full registration. Guest accounts are deactivated by default; to
activate them, add the following line to your settings file:

    GUEST_ENABLED = True

You will also need to modify the connection screen to reflect the
possibility to connect with a guest account. The setting file accepts
several more options for customizing the Guest account system.

"""

from evennia.accounts.accounts import DefaultAccount, DefaultGuest
from evennia.commands.default.cmdset_account import AccountCmdSet
from evennia.utils import evmenu
from evennia.utils.utils import is_iter

from evennia import AttributeProperty


class Account(DefaultAccount):
    """
    An Account is the actual OOC player entity. It doesn't exist in the game,
    but puppets characters.

    This is the base Typeclass for all Accounts. Accounts represent
    the person playing the game and tracks account info, password
    etc. They are OOC entities without presence in-game. An Account
    can connect to a Character Object in order to "enter" the
    game.

    Account Typeclass API:

    * Available properties (only available on initiated typeclass objects)

     - key (string) - name of account
     - name (string)- wrapper for user.username
     - aliases (list of strings) - aliases to the object. Will be saved to
            database as AliasDB entries but returned as strings.
     - dbref (int, read-only) - unique #id-number. Also "id" can be used.
     - date_created (string) - time stamp of object creation
     - permissions (list of strings) - list of permission strings
     - user (User, read-only) - django User authorization object
     - obj (Object) - game object controlled by account. 'character' can also
                     be used.
     - is_superuser (bool, read-only) - if the connected user is a superuser

    * Handlers

     - locks - lock-handler: use locks.add() to add new lock strings
     - db - attribute-handler: store/retrieve database attributes on this
                              self.db.myattr=val, val=self.db.myattr
     - ndb - non-persistent attribute handler: same as db but does not
                                  create a database entry when storing data
     - scripts - script-handler. Add new scripts to object with scripts.add()
     - cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     - nicks - nick-handler. New nicks with nicks.add().
     - sessions - session-handler. Use session.get() to see all sessions connected, if any
     - options - option-handler. Defaults are taken from settings.OPTIONS_ACCOUNT_DEFAULT
     - characters - handler for listing the account's playable characters

    * Helper methods (check autodocs for full updated listing)

     - msg(text=None, from_obj=None, session=None, options=None, **kwargs)
     - execute_cmd(raw_string)
     - search(searchdata, return_puppet=False, search_object=False, typeclass=None,
                      nofound_string=None, multimatch_string=None, use_nicks=True,
                      quiet=False, **kwargs)
     - is_typeclass(typeclass, exact=False)
     - swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     - access(accessing_obj, access_type='read', default=False, no_superuser_bypass=False, **kwargs)
     - check_permstring(permstring)
     - get_cmdsets(caller, current, **kwargs)
     - get_cmdset_providers()
     - uses_screenreader(session=None)
     - get_display_name(looker, **kwargs)
     - get_extra_display_name_info(looker, **kwargs)
     - disconnect_session_from_account()
     - puppet_object(session, obj)
     - unpuppet_object(session)
     - unpuppet_all()
     - get_puppet(session)
     - get_all_puppets()
     - is_banned(**kwargs)
     - get_username_validators(validator_config=settings.AUTH_USERNAME_VALIDATORS)
     - authenticate(username, password, ip="", **kwargs)
     - normalize_username(username)
     - validate_username(username)
     - validate_password(password, account=None)
     - set_password(password, **kwargs)
     - get_character_slots()
     - get_available_character_slots()
     - create_character(*args, **kwargs)
     - create(*args, **kwargs)
     - delete(*args, **kwargs)
     - channel_msg(message, channel, senders=None, **kwargs)
     - idle_time()
     - connection_time()

    * Hook methods

     basetype_setup()
     at_account_creation()

     > note that the following hooks are also found on Objects and are
       usually handled on the character level:

     - at_init()
     - at_first_save()
     - at_access()
     - at_cmdset_get(**kwargs)
     - at_password_change(**kwargs)
     - at_first_login()
     - at_pre_login()
     - at_post_login(session=None)
     - at_failed_login(session, **kwargs)
     - at_disconnect(reason=None, **kwargs)
     - at_post_disconnect(**kwargs)
     - at_message_receive()
     - at_message_send()
     - at_server_reload()
     - at_server_shutdown()
     - at_look(target=None, session=None, **kwargs)
     - at_post_create_character(character, **kwargs)
     - at_post_add_character(char)
     - at_post_remove_character(char)
     - at_pre_channel_msg(message, channel, senders=None, **kwargs)
     - at_post_chnnel_msg(message, channel, senders=None, **kwargs)

    """

    wallet_address = AttributeProperty(default=None)
    chain_id = AttributeProperty(default=None)
    subscription_expires_date = AttributeProperty(default=None)

    ooc_appearance_template = """
-
|b--------------------------------------------------------------|n
|wFull Circle MUD - Main Menu|n
|b--------------------------------------------------------------|n
{header}
{sessions}
{subscription}
|wYour Characters:|n  {footer}
|b--------------------------------------------------------------|n
{characters}
|wCharacter Commands:|n
|b--------------------------------------------------------------|n
Enter Game (In Character)   |gic <charname>|n
Create Character            |gcharcreate|n   
Delete Character            |gchardelete <charname>|n

|wBank Commands:|n
|b--------------------------------------------------------------|n
In game bank asset list     |gbank|n
Out of game asset list      |gwallet|n
Import assets into game     |gimport gold <amount>|n
                            |gimport <resource> <amount>|n
                            |gimport nft|n
Export assets out of game   |gexport gold <amount>|n
                            |gexport <resource> <amount>|n
                            |gexport <token_id>|n

|wGeneral Commands:|n
|b--------------------------------------------------------------|n
Help                        |ghelp|n  
Leave Character / Game      |gquit|n
|b--------------------------------------------------------------|n
""".strip()

    def create_character(self, *args, **kwargs):
        """Place new characters at The Harvest Moon inn instead of Limbo."""
        if "location" not in kwargs:
            inn = ObjectDB.objects.filter(db_key="The Harvest Moon").first()
            if inn:
                kwargs["location"] = inn
        return super().create_character(*args, **kwargs)

    def _build_subscription_line(self):
        """Build the subscription status line for the OOC menu."""
        from django.conf import settings as _settings
        if not getattr(_settings, "SUBSCRIPTION_ENABLED", False):
            return ""

        from subscriptions.utils import get_subscription_status

        status = get_subscription_status(self)

        if status["is_exempt"]:
            return ""

        if not status["subscribed"]:
            return (
                "|r*** Your subscription has expired ***|n\n"
                "|rUse |wsubscribe|r to renew your subscription.|n"
            )

        expiry = status["expiry"]
        if status["is_warning"]:
            hours = status["hours_remaining"]
            h = int(hours)
            m = int((hours - h) * 60)
            return (
                f"|r*** Your subscription expires in "
                f"{h} hours and {m} minutes ***|n\n"
                f"|rUse |wsubscribe|r to extend your subscription.|n"
            )

        expiry_str = expiry.strftime("%H:%M UTC on %d %B %Y")
        return f"Subscribed until {expiry_str}"

    def at_look(self, target=None, session=None, **kwargs):
        """
        Called when this object executes a look. It allows to customize
        just what this means.

        Args:
            target (Object or list, optional): An object or a list
                objects to inspect. This is normally a list of characters.
            session (Session, optional): The session doing this look.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        Returns:
            look_string (str): A prepared look string, ready to send
                off to any recipient (usually to ourselves)

        """

        if target and not is_iter(target):
            # single target - just show it
            if hasattr(target, "return_appearance"):
                return target.return_appearance(self)
            else:
                return f"{target} has no in-game appearance."

        
        sessions = self.sessions.all()
        nsess = len(sessions)

        if not nsess:
            # no sessions, nothing to report
            return ""
        
        # multiple targets - this is a list of characters
        characters = list(tar for tar in target if tar) if target else []
        #ncars = len(characters)
        ncars = len(characters) if characters is not None else 0
        max_chars = (
            "unlimited"
            if self.is_superuser or _MAX_NR_CHARACTERS is None
            else _MAX_NR_CHARACTERS
        )

        # header text
        #txt_header = f"Account |g{self.name}|n (you are Out-of-Character)"
        txt_header = f"Account Username: |g{self.name}|n"

        # sessions
        sess_strings = []
        for isess, sess in enumerate(sessions):
            ip_addr = sess.address[0] if isinstance(sess.address, tuple) else sess.address
            #addr = f"{sess.protocol_key} ({ip_addr})"
            addr = f"({ip_addr})"
            sess_str = (
                f"|w* {isess + 1}|n"
                if session and session.sessid == sess.sessid
                else f"  {isess + 1}"
            )

            #sess_strings.append(f"{sess_str} {addr}")
            sess_strings.append(f"{addr}")


        
        txt_sessions = f"Wallet Address: |g{self.wallet_address}|n"

        if not txt_sessions:
            txt_sessions = "None"
        
        txt_footer = f"( {ncars} of {max_chars} used )"

        # Build subscription status line
        txt_subscription = self._build_subscription_line()

        if not characters:
            txt_characters = "You don't have a character yet.\n"
        else:


            #get the width of the largest characters name
            # so all character names can be aligned equally
            max_length = 10
            for char in characters:
                if len(char.key) > max_length:
                    max_length = len(char.key)


            # generate the listing of character names
            char_listing = ""
            for char in characters:
                char_listing += f"|r{char.key:^{max_length + 3}}|n |     {char.get_class_string()}\n"

            txt_characters = (char_listing)


        return self.ooc_appearance_template.format(
            header=txt_header,
            sessions=txt_sessions,
            subscription=txt_subscription,
            characters=txt_characters,
            footer=txt_footer,
        )

    
    @classmethod
    def create(cls, *args, **kwargs):
        """
        Creates an Account (or Account/Character pair for MULTISESSION_MODE<2)
        with default (or overridden) permissions and having joined them to the
        appropriate default channels.

        Keyword Args:
            username (str): Username of Account owner
            password (str): Password of Account owner
            email (str, optional): Email address of Account owner
            ip (str, optional): IP address of requesting connection
            guest (bool, optional): Whether or not this is to be a Guest account

            permissions (str, optional): Default permissions for the Account
            typeclass (str, optional): Typeclass to use for new Account
            character_typeclass (str, optional): Typeclass to use for new char
                when applicable.

        Returns:
            account (Account): Account if successfully created; None if not
            errors (list): List of error messages in string form

        """

        account = None
        errors = []

        username = kwargs.get("username", "")
        # password not used but default value passed through to avoid refactoring any password logic downstream
        password = kwargs.get("password", "")
        email = kwargs.get("email", "").strip()
        guest = kwargs.get("guest", False)

        wallet_address = kwargs.get("wallet_address")
        session = kwargs.get("session")
        
        ip = kwargs.get("ip", "")
        if isinstance(ip, (tuple, list)):
            ip = ip[0]
    
        permissions = kwargs.get("permissions", settings.PERMISSION_ACCOUNT_DEFAULT)
        typeclass = kwargs.get("typeclass", cls)


        if ip and CREATION_THROTTLE.check(ip):
            errors.append(
                _("You are creating too many accounts. Please log into an existing account.")
            )
            return None, errors

        # Normalize username
        username = cls.normalize_username(username)

        # Validate username
        if not guest:
            valid, errs = cls.validate_username(username)
            if not valid:
                # this echoes the restrictions made by django's auth
                # module (except not allowing spaces, for convenience of
                # logging in).
                errors.extend(errs)
                return None, errors

        # leavng it in with the default password being passed through
        # Validate password
        # Have to create a dummy Account object to check username similarity
        valid, errs = cls.validate_password(password, account=cls(username=username))
        if not valid:
            errors.extend(errs)
            return None, errors
        

        # Check IP and/or name bans
        banned = cls.is_banned(username=username, ip=ip)
        if banned:
            # this is a banned IP or name!
            string = _(
                "|rYou have been banned and cannot continue from here."
                "\nIf you feel this ban is in error, please email an admin.|x"
            )
            errors.append(string)
            return None, errors

        # everything's ok. Create the new account.
        try:
            try:
                account = create.create_account(
                    username, email, password, permissions=permissions, typeclass=typeclass
                )
                logger.log_sec(f"Account Created: {account} (IP: {ip}).")

                account.wallet_address = wallet_address

            except Exception:
                errors.append(
                    _(
                        "There was an error creating the Account. "
                        "If this problem persists, contact an admin."
                    )
                )
                logger.log_trace()
                return None, errors

            # This needs to be set so the engine knows this account is
            # logging in for the first time. (so it knows to call the right
            # hooks during login later)
            account.db.FIRST_LOGIN = True

            # Record IP address of creation, if available
            if ip:
                account.db.creator_ip = ip

            # join the new account to the public channels
            for chan_info in settings.DEFAULT_CHANNELS:
                if chankey := chan_info.get("key"):
                    channel = ChannelDB.objects.get_channel(chankey)
                    if not channel or not (
                        channel.access(account, "listen") and channel.connect(account)
                    ):
                        string = (
                            f"New account '{account.key}' could not connect to default channel"
                            f" '{chankey}'!"
                        )
                        logger.log_err(string)
                else:
                    logger.log_err(f"Default channel '{chan_info}' is missing a 'key' field!")

            if account and _AUTO_CREATE_CHARACTER_WITH_ACCOUNT:
                # Auto-create a character to go with this account

                character, errs = account.create_character(
                    typeclass=kwargs.get("character_typeclass", account.default_character_typeclass)
                )
                if errs:
                    errors.extend(errs)

        except Exception:
            # We are in the middle between logged in and -not, so we have
            # to handle tracebacks ourselves at this point. If we don't,
            # we won't see any errors at all.
            errors.append(_("An error occurred. Please e-mail an admin if the problem persists."))
            logger.log_trace()

        # Update the throttle to indicate a new account was created from this IP
        if ip and not guest:
            CREATION_THROTTLE.update(ip, "Too many accounts being created.")
        SIGNAL_ACCOUNT_POST_CREATE.send(sender=account, ip=ip)
        return account, errors


    def at_account_creation(self):
        """
        This is called once, the very first time the account is created
        (i.e. first time they register with the game). It's a good
        place to store attributes all accounts should have, like
        configuration values etc.

        """

        # set an (empty) attribute holding the characters this account has
        lockstring = "attrread:perm(Admins);attredit:perm(Admins);attrcreate:perm(Admins);"
        self.attributes.add("_playable_characters", [], lockstring=lockstring)
        self.attributes.add("_saved_protocol_flags", {}, lockstring=lockstring)


        # Skip bank creation for the superuser (#1) — it's created during
        # `evennia migrate` before Limbo exists, so the bank objects would
        # steal early dbref slots (#2, #3) that Evennia expects for Limbo.
        if not self.is_superuser:
            bank = create_object(
                "typeclasses.accounts.account_bank.AccountBank",
                key=f"bank-{self.key}",
                nohome=True,       # no physical home location needed
            )
            bank.wallet_address = self.wallet_address
            self.db.bank = bank   # stores the dbref, auto-resolves on access

            # Grant free trial subscription
            from subscriptions.utils import grant_trial

            grant_trial(self)

    def at_post_login(self, session=None, **kwargs):
        """Called after login. Backfills wallet + bank for the superuser."""
        super().at_post_login(session=session, **kwargs)

        from blockchain.xrpl.cosigner_ping import warm_cosigner
        warm_cosigner()

        if self.is_superuser and not self.wallet_address:
            self.wallet_address = settings.SUPERUSER_XRPL_WALLET_ADDRESS
            self.msg(f"|y[Dev] Superuser wallet set to: {settings.SUPERUSER_XRPL_WALLET_ADDRESS}|n")

        if self.db.bank is None:
            bank = create_object(
                "typeclasses.accounts.account_bank.AccountBank",
                key=f"bank-{self.key}",
                nohome=True,
            )
            bank.wallet_address = self.wallet_address
            self.db.bank = bank
            self.msg("|y[Dev] Bank created for account.|n")
            self.msg(
                "\n|r============================================|n"
                "\n|r  REMINDER: Run these commands (OOC):       |n"
                "\n|r    sync_nfts      — sync on-chain NFTs     |n"
                "\n|r    sync_reserves  — recalculate reserves    |n"
                "\n|r    reconcile      — verify balances match   |n"
                "\n|r============================================|n"
            )

        # Grant all languages to superuser characters
        if self.is_superuser:
            from enums.languages import Languages
            all_langs = {lang.value for lang in Languages}
            for char in self.characters.all():
                char.db.languages = all_langs

        # ── Login history ──────────────────────────────────────────
        # Record IP (hashed per privacy policy) and geo-country for each
        # login.  Gated by LOG_PLAYER_GEO_DATA — disabled by default,
        # enable in settings.py if jurisdictional tracking is needed.
        if session is not None and getattr(settings, "LOG_PLAYER_GEO_DATA", False):
            import hashlib
            from datetime import datetime, timezone as _tz

            raw_addr = getattr(session, "address", None)
            ip_str = str(raw_addr[0]) if isinstance(raw_addr, (list, tuple)) else str(raw_addr or "unknown")
            ip_hash = hashlib.sha256(ip_str.encode()).hexdigest()

            server_data = getattr(session, "server_data", None) or {}
            country = server_data.get("geo_country", "XX") or "XX"

            entry = {
                "ip_hash": ip_hash,
                "country": country,
                "timestamp": datetime.now(_tz.utc).isoformat(),
            }

            history = list(self.db.login_history or [])
            history.append(entry)
            if len(history) > 50:
                history = history[-50:]
            self.db.login_history = history

        # ── ToS re-acceptance check ────────────────────────────────
        # Skip for superuser — they're never blocked from the game
        if not self.is_superuser and session is not None:
            current_tos = getattr(settings, "TOS_VERSION", None)
            accepted_tos = self.db.tos_version
            if current_tos and accepted_tos != current_tos:
                _prompt_tos_reaccept(self, session, current_tos)
                return

        # ── Auto-resume previous IC session on reconnect ───────────
        self._try_reconnect_puppet(session)

    # ------------------------------------------------------------------
    # Reconnect-to-state: graceful logout tracking
    # ------------------------------------------------------------------

    def mark_graceful_logout(self):
        """Call before unpuppet in ooc/quit/rent/chardelete paths.

        Sets the one-shot ``graceful_logout`` flag (consumed on next
        login) and clears ``active_puppet_id`` so the next connection
        falls through to the OOC menu instead of auto-resuming.
        """
        self.db.graceful_logout = True
        self.attributes.remove("active_puppet_id")

    def _try_reconnect_puppet(self, session):
        """Auto-repuppet the last active character on linkdead/restart reconnect.

        Fresh connects and graceful logouts fall through to the OOC menu.
        Reconnects (linkdead or server restart while puppeted) resume the
        character in place.
        """
        if session is None or self.is_superuser or isinstance(self, Guest):
            return

        if self.db.graceful_logout:
            self.attributes.remove("graceful_logout")
            return

        puppet_id = self.db.active_puppet_id
        if not puppet_id:
            return

        try:
            char = ObjectDB.objects.get(pk=puppet_id)
        except ObjectDB.DoesNotExist:
            self.attributes.remove("active_puppet_id")
            return

        if char not in make_iter(self.characters):
            self.attributes.remove("active_puppet_id")
            return

        from subscriptions.utils import is_subscribed

        if not is_subscribed(self):
            self.attributes.remove("active_puppet_id")
            self.msg(
                "|yYour subscription has expired — use |wsubscribe|y to renew.|n"
            )
            return

        try:
            self.puppet_object(session, char)
        except RuntimeError as exc:
            logger.log_trace(f"Auto-resume failed for {self}: {exc}")
            self.attributes.remove("active_puppet_id")
            self.msg(
                "|rCould not auto-resume your last character. "
                "Use |wic <name>|r to play.|n"
            )
            return

        self.msg(f"|gResuming as {char.key}...|n")
        char.execute_cmd("look")


def _prompt_tos_reaccept(account, session, current_tos):
    """Show ToS re-acceptance prompt to a logged-in player."""
    from evennia.utils.evmenu import get_input

    website_url = getattr(settings, "GAME_WEBSITE_URL", "https://fcmud.world")
    prompt = (
        "\n|c--- Terms of Service Updated ---|n"
        "\nOur Terms of Service have been updated since you last agreed."
        f"\n\nRead the updated Terms of Service at:"
        f"\n|w{website_url}/terms/|n"
        "\n\nBy continuing to play you agree to be bound by the updated terms,"
        "\nincluding the jurisdictional restrictions on the gold redemption feature."
        "\n\nDo you agree to the updated Terms of Service? Y/[N]: "
    )
    get_input(account, prompt, _handle_tos_reaccept, session=session, tos_version=current_tos)


def _handle_tos_reaccept(caller, prompt, result, session=None, tos_version=None):
    """
    Callback for get_input() — handles ToS re-acceptance on login.

    Defaults to No if the player just presses Enter without typing Y.
    Returns False to finish the prompt chain.
    """
    account = caller

    if result.strip().lower() not in ("y", "yes"):
        account.msg(
            "\n|rYou must agree to the updated Terms of Service to continue playing.|n"
            "\nYour session has been disconnected."
            "\nType |wconnect|n and agree to the Terms of Service to play again."
        )
        if session:
            from evennia.server.sessionhandler import SESSIONS
            account.mark_graceful_logout()
            SESSIONS.disconnect(session, reason="ToS not accepted.")
        return False

    # Accepted — record updated version and timestamp
    from datetime import datetime, timezone
    account.db.tos_version = tos_version
    account.db.tos_agreed_at = datetime.now(timezone.utc).isoformat()
    account.msg(
        "\n|gThank you — Terms of Service accepted.|n"
        "\nWelcome back!\n"
    )
    # Show the main menu again so the player can proceed
    account.msg(account.at_look(session=session))
    return False


class Guest(DefaultGuest):
    """
    This class is used for guest logins. Unlike Accounts, Guests and their
    characters are deleted after disconnection.
    """

    pass

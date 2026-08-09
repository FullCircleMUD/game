"""
Superuser command: reset a bot account to clean state.

Deletes all characters on the bot account, leaving the account
itself intact with its wallet address.

Bot accounts are testing/dev tooling (an LLM harness logging in the
front door like a normal player) — this is manual, multi-step tooling
by design, not automated cross-shard dispatch, matching that scope.
"""

from django.conf import settings
from evennia import Command


class CmdBotReset(Command):
    """
    Reset a bot account by deleting all its characters.

    Usage:
        botreset <botname>
        botreset all

    On the router: lists each bot's characters and which shard each one
    lives on, then tells you which shards to re-run the command on —
    it does not delete anything itself, since a character can only be
    deleted from the shard (or monolith) that actually hosts it.

    On a shard (or in monolith): deletes whichever of the target
    character(s) are resident here (characters on other shards are
    invisible from here by design — that's what the router's shard
    list is for). The account itself is preserved with its wallet
    address.
    """

    key = "botreset"
    locks = "cmd:id(1)"
    help_category = "Bots"

    def func(self):
        from evennia.accounts.models import AccountDB
        from evennia_shards import ROLE_ROUTER, get_role

        if not self.args or not self.args.strip():
            self.msg("Usage: botreset <botname> OR botreset all")
            return

        target = self.args.strip().lower()
        usernames = getattr(settings, "BOT_ACCOUNT_USERNAMES", [])

        if target == "all":
            names_to_reset = list(usernames)
        else:
            if target not in usernames:
                self.msg(
                    f"|r{target}|n is not in BOT_ACCOUNT_USERNAMES. "
                    f"Configured: {', '.join(usernames)}"
                )
                return
            names_to_reset = [target]

        if get_role() == ROLE_ROUTER:
            self._list_shards(names_to_reset)
            return

        total_deleted = 0
        for name in names_to_reset:
            account = AccountDB.objects.filter(username=name).first()
            if not account:
                self.msg(f"  |y{name}|n: account doesn't exist, skipping.")
                continue

            puppets = account.db._playable_characters or []
            if not puppets:
                self.msg(f"  |y{name}|n: no characters to delete here.")
                continue

            count = 0
            for char in list(puppets):
                char_name = char.key
                char.delete()
                count += 1
                self.msg(f"  |r{name}|n: deleted character '{char_name}'")
            total_deleted += count

        self.msg(f"\n|gReset complete.|n Deleted {total_deleted} character(s) here.")

    def _list_shards(self, names):
        """Router-only: show each bot's characters and where they live."""
        from evennia.accounts.models import AccountDB

        shard_ids = set()
        found_any = False

        for name in names:
            account = AccountDB.objects.filter(username=name).first()
            if not account:
                self.msg(f"  |y{name}|n: account doesn't exist, skipping.")
                continue

            puppets = account.db._playable_characters or []
            if not puppets:
                self.msg(f"  |y{name}|n: no characters.")
                continue

            for char in puppets:
                found_any = True
                shard_id = getattr(char, "shard_id", None) or "unknown"
                shard_ids.add(shard_id)
                self.msg(f"  |w{name}|n: '{char.key}' on |c{shard_id}|n")

        if not found_any:
            self.msg("\n|gNothing found — nothing to reset.|n")
            return

        self.msg(
            f"\n|yThe router can't delete characters directly. Connect to "
            f"each of these shards and run 'botreset {self.args.strip()}' "
            f"there: {', '.join(sorted(shard_ids))}|n"
        )

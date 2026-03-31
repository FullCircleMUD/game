"""
Superuser command: reset a bot account to clean state.

Deletes all characters on the bot account, leaving the account
itself intact with its wallet address.
"""

from django.conf import settings
from evennia import Command


class CmdBotReset(Command):
    """
    Reset a bot account by deleting all its characters.

    Usage:
        botreset <botname>
        botreset all

    Deletes all characters belonging to the named bot account.
    The account itself is preserved with its wallet address.
    Use 'botreset all' to reset every configured bot account.
    """

    key = "botreset"
    locks = "cmd:id(1)"
    help_category = "System"

    def func(self):
        from evennia.accounts.models import AccountDB

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

        total_deleted = 0
        for name in names_to_reset:
            account = AccountDB.objects.filter(username=name).first()
            if not account:
                self.msg(f"  |y{name}|n: account doesn't exist, skipping.")
                continue

            puppets = account.db._playable_characters or []
            if not puppets:
                self.msg(f"  |y{name}|n: no characters to delete.")
                continue

            count = 0
            for char in list(puppets):
                char_name = char.key
                char.delete()
                count += 1
                self.msg(f"  |r{name}|n: deleted character '{char_name}'")
            total_deleted += count

        self.msg(f"\n|gReset complete.|n Deleted {total_deleted} character(s).")

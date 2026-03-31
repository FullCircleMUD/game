"""
Superuser command: list bot account status.

Shows all configured bot accounts with their existence status,
wallet address, and character count.
"""

from django.conf import settings
from evennia import Command


class CmdBotList(Command):
    """
    Show status of all configured bot accounts.

    Usage:
        botlist

    Lists each bot account from BOT_ACCOUNT_USERNAMES with:
    - Whether the account exists
    - Wallet address (configured vs actual)
    - Number of characters
    - Character names and levels
    """

    key = "botlist"
    locks = "cmd:id(1)"
    help_category = "System"

    def func(self):
        from evennia.accounts.models import AccountDB

        usernames = getattr(settings, "BOT_ACCOUNT_USERNAMES", [])
        wallets = getattr(settings, "BOT_WALLET_ADDRESSES", {})

        if not usernames:
            self.msg("No bot accounts configured in BOT_ACCOUNT_USERNAMES.")
            return

        self.msg("|wBot Account Status|n")
        self.msg("|b" + "-" * 62 + "|n")

        for name in usernames:
            account = AccountDB.objects.filter(username=name).first()

            if not account:
                self.msg(f"  |r{name}|n: NOT CREATED")
                continue

            wallet_actual = account.attributes.get("wallet_address")
            wallet_config = wallets.get(name)

            # Wallet status
            if wallet_actual and wallet_actual == wallet_config:
                wallet_str = f"|g{wallet_actual}|n"
            elif wallet_actual and wallet_config and wallet_actual != wallet_config:
                wallet_str = f"|y{wallet_actual}|n (mismatch — config: {wallet_config})"
            elif wallet_actual:
                wallet_str = f"|y{wallet_actual}|n (not in config)"
            else:
                wallet_str = "|rNone|n"

            # Characters
            puppets = account.db._playable_characters or []
            if puppets:
                char_strs = []
                for char in puppets:
                    level = getattr(char, "total_level", "?")
                    char_strs.append(f"{char.key} (L{level})")
                chars_str = ", ".join(char_strs)
            else:
                chars_str = "none"

            self.msg(f"  |g{name}|n (#{account.id})")
            self.msg(f"    Wallet: {wallet_str}")
            self.msg(f"    Characters: {chars_str}")

        self.msg("|b" + "-" * 62 + "|n")
        self.msg(f"BOT_LOGIN_ENABLED: |w{getattr(settings, 'BOT_LOGIN_ENABLED', False)}|n")

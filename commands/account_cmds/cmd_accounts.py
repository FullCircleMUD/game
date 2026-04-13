"""
Superuser command: list all accounts and last login time.
"""

from evennia import Command


class CmdAccounts(Command):
    """
    List all accounts with last login time.

    Usage:
        accounts

    Shows every account with their ID, last login timestamp,
    online status, and characters.
    """

    key = "accounts"
    locks = "cmd:id(1)"
    help_category = "Admin"

    def func(self):
        from evennia.accounts.models import AccountDB

        accounts = AccountDB.objects.all().order_by("-last_login")

        if not accounts.exists():
            self.msg("No accounts found.")
            return

        self.msg("|wAll Accounts|n")
        self.msg("|b" + "-" * 72 + "|n")

        for acct in accounts:
            # Last login
            if acct.last_login:
                login_str = acct.last_login.strftime("%Y-%m-%d %H:%M")
            else:
                login_str = "Never"

            # Online status
            online = "|g*|n " if acct.sessions.count() > 0 else "  "

            # Characters
            puppets = acct.db._playable_characters or []
            if puppets:
                chars = ", ".join(p.key for p in puppets)
            else:
                chars = "-"

            self.msg(
                f"  {online}|w{acct.username}|n (#{acct.id})  "
                f"Last login: {login_str}  Chars: {chars}"
            )

        self.msg("|b" + "-" * 72 + "|n")
        self.msg(f"Total: |w{accounts.count()}|n accounts")

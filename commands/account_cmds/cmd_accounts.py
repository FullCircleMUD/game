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
    characters, and whether they have a session connected to
    THIS process — not cluster-wide online status. A player IC
    on a different shard shows as offline here even though they
    are connected elsewhere; hop shards and re-run to check each
    one, or see docs/scaling.md's open TBD on cross-shard presence.
    """

    key = "accounts"
    locks = "cmd:id(1)"
    help_category = "Admin"

    def func(self):
        from evennia.accounts.models import AccountDB
        from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role, get_shard_id

        role = get_role()
        if role == ROLE_MONOLITH:
            process_label = "monolith"
        elif role == ROLE_ROUTER:
            process_label = "router"
        else:
            process_label = get_shard_id() or role

        accounts = AccountDB.objects.all().order_by("-last_login")

        if not accounts.exists():
            self.msg("No accounts found.")
            return

        self.msg("|wAll Accounts|n")
        self.msg(f"|c(Online = connected to this process: {process_label})|n")
        self.msg("|b" + "-" * 72 + "|n")

        for acct in accounts:
            # Last login
            if acct.last_login:
                login_str = acct.last_login.strftime("%Y-%m-%d %H:%M")
            else:
                login_str = "Never"

            # Online on this process only — see command docstring.
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

from evennia.commands.default.account import CmdOOC as _CmdOOC


class CmdOOC(_CmdOOC):
    """Superuser-only OOC.

    Players use ``rent`` or ``quit`` to leave the playing surface.
    ``ooc`` is retained for admins so they can detach a session from a
    character without going through the rent/quit flow (e.g. during
    debugging or live troubleshooting).
    """

    help_category = "System"
    locks = "cmd:perm(Developer)"

    def func(self):
        account = self.account
        session = self.session
        if account and account.get_puppet(session):
            account.mark_graceful_logout()
        super().func()

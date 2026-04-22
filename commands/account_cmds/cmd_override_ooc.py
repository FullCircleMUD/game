from evennia.commands.default.account import CmdOOC as _CmdOOC


class CmdOOC(_CmdOOC):
    help_category = "System"

    def func(self):
        account = self.account
        session = self.session
        if account and account.get_puppet(session):
            account.mark_graceful_logout()
        super().func()

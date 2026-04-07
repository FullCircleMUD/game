from evennia.commands.default.account import CmdIC as _CmdIC

from subscriptions.utils import is_subscribed


class CmdIC(_CmdIC):
    help_category = "System"

    def func(self):
        if not is_subscribed(self.account):
            self.msg(
                "|rYour subscription has expired.|n\n"
                "Use |wsubscribe|n to renew."
            )
            return
        super().func()

from evennia.commands.default.general import CmdAccess as _CmdAccess
from evennia.objects.objects import DefaultObject
from evennia.utils import utils

from commands.command import FCMCommandMixin


class CmdAccess(FCMCommandMixin, _CmdAccess):
    """
    Show your current game access.

    Usage:
        access

    This command shows which permission groups you are a member of.
    """

    help_category = "System"

    def func(self):
        """Show the caller's own permissions only — no full hierarchy."""
        caller = self.caller

        if caller.account and caller.account.is_superuser:
            cperms = "<Superuser>"
            pperms = "<Superuser>"
        else:
            cperms = ", ".join(caller.permissions.all())
            if caller.account:
                pperms = ", ".join(caller.account.permissions.all())
            else:
                pperms = "<No account>"

        string = "|wYour access|n:"
        string += f"\nCharacter |c{caller.key}|n: {cperms}"
        if utils.inherits_from(caller, DefaultObject) and caller.account:
            string += f"\nAccount |c{caller.account.key}|n: {pperms}"
        caller.msg(string)

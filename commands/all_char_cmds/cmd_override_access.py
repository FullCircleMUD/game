from evennia.commands.default.general import CmdAccess as _CmdAccess

from commands.command import FCMCommandMixin


class CmdAccess(FCMCommandMixin, _CmdAccess):
    help_category = "System"

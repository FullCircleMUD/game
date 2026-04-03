from evennia.commands.default.general import CmdNick as _CmdNick

from commands.command import FCMCommandMixin


class CmdNick(FCMCommandMixin, _CmdNick):
    help_category = "System"
    aliases = ["alias"]

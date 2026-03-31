from evennia.commands.default.general import CmdNick as _CmdNick


class CmdNick(_CmdNick):
    help_category = "System"
    aliases = ["alias"]

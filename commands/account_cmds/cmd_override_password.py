from evennia.commands.default.account import CmdPassword as _CmdPassword


class CmdPassword(_CmdPassword):
    locks = "cmd:id(1)"
    help_category = "System"

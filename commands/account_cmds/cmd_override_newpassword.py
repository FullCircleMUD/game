from evennia.commands.default.admin import CmdNewPassword as _CmdNewPassword


class CmdNewPassword(_CmdNewPassword):
    locks = "cmd:id(1)"
    help_category = "System"

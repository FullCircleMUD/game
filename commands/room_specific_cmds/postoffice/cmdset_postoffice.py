"""CmdSet for Post Office rooms."""

from evennia import CmdSet

from commands.room_specific_cmds.postoffice.cmd_mail import CmdMail


class CmdSetPostOffice(CmdSet):
    """Commands available in Post Office rooms."""

    key = "CmdSetPostOffice"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdMail())

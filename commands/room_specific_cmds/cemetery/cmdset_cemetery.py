from evennia import CmdSet

from commands.room_specific_cmds.cemetery.cmd_bind import CmdBind


class CmdSetCemetery(CmdSet):

    key = "CmdSetCemetery"

    def at_cmdset_creation(self):
        self.add(CmdBind())

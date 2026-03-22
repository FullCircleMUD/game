from evennia import CmdSet

from commands.room_specific_cmds.purgatory.cmd_release import CmdRelease


class CmdSetPurgatory(CmdSet):

    key = "CmdSetPurgatory"

    def at_cmdset_creation(self):
        self.add(CmdRelease())

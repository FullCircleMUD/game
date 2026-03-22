from evennia import CmdSet

from commands.room_specific_cmds.harvesting.cmd_harvest import CmdHarvest


class CmdSetHarvesting(CmdSet):

    key = "CmdSetHarvesting"

    def at_cmdset_creation(self):
        self.add(CmdHarvest())

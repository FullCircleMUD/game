from evennia import CmdSet

from commands.room_specific_cmds.processing.cmd_process import CmdProcess
from commands.room_specific_cmds.processing.cmd_rates import CmdRates


class CmdSetProcessing(CmdSet):

    key = "CmdSetProcessing"

    def at_cmdset_creation(self):
        self.add(CmdProcess())
        self.add(CmdRates())

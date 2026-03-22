"""CmdSet for gateway rooms."""

from evennia import CmdSet

from commands.room_specific_cmds.gateway.cmd_travel import CmdTravel
from commands.room_specific_cmds.gateway.cmd_explore import CmdExplore


class CmdSetGateway(CmdSet):
    key = "GatewayCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdTravel())
        self.add(CmdExplore())

from evennia import CmdSet

from commands.room_specific_cmds.crafting.cmd_craft import CmdCraft
from commands.room_specific_cmds.crafting.cmd_available import CmdAvailable
from commands.room_specific_cmds.crafting.cmd_inset import CmdInset
from commands.room_specific_cmds.crafting.cmd_repair import CmdRepair


class CmdSetCrafting(CmdSet):

    key = "CmdSetCrafting"

    def at_cmdset_creation(self):
        self.add(CmdCraft())
        self.add(CmdAvailable())
        self.add(CmdInset())
        self.add(CmdRepair())

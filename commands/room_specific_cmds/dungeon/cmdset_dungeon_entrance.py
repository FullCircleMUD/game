"""CmdSet for dungeon entrance rooms."""

from evennia import CmdSet

from commands.room_specific_cmds.dungeon.cmd_enter_dungeon import CmdEnterDungeon


class CmdSetDungeonEntrance(CmdSet):
    key = "DungeonEntranceCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdEnterDungeon())

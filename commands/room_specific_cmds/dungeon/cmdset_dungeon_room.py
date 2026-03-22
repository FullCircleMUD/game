"""CmdSet for dungeon rooms (provides exit dungeon command)."""

from evennia import CmdSet

from commands.room_specific_cmds.dungeon.cmd_dungeon_exit import CmdExitDungeon


class CmdSetDungeonRoom(CmdSet):
    key = "DungeonRoomCmdSet"

    def at_cmdset_creation(self):
        self.add(CmdExitDungeon())

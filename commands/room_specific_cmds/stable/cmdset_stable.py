"""
Stable command set — added to RoomStable rooms.
"""

from evennia import CmdSet

from commands.room_specific_cmds.stable.cmd_stable import (
    CmdStable, CmdRetrieve, CmdStabled,
)


class CmdSetStable(CmdSet):
    key = "CmdSetStable"

    def at_cmdset_creation(self):
        self.add(CmdStable())
        self.add(CmdRetrieve())
        self.add(CmdStabled())

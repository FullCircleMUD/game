"""CmdSet for TradingPost objects."""

from evennia import CmdSet

from commands.room_specific_cmds.trading_post.cmd_trading_post import (
    CmdBrowse,
    CmdPost,
    CmdRemoveListing,
)


class TradingPostCmdSet(CmdSet):
    """Commands available when a TradingPost object is in the room."""

    key = "TradingPostCmdSet"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdBrowse())
        self.add(CmdPost())
        self.add(CmdRemoveListing())

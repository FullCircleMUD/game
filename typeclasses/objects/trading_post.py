"""
Trading Post — placeable bulletin board for trade listings.

Builders place these in town squares. All boards read from the same
global BulletinListing table — post in one town, visible everywhere.
"""

from evennia import DefaultObject

from commands.room_specific_cmds.trading_post.cmdset_trading_post import TradingPostCmdSet


class TradingPost(DefaultObject):
    """A bulletin board for player trade listings."""

    def at_object_creation(self):
        super().at_object_creation()
        self.locks.add("get:false()")
        self.db.desc = "A large wooden notice board covered in pinned listings."
        self.cmdset.add(TradingPostCmdSet, persistent=True)

"""
CmdRecall — return to the library from a book zone.

Teleports the player back to the room they were in when they read a
library book. Clears the saved return location after use.

Usage:
    recall
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdRecall(FCMCommandMixin, Command):
    """
    Return to the library from a book zone.

    Usage:
        recall

    Transports you back to the library room you entered the book
    from. Only works if you entered a book zone via |wread|n.
    """

    key = "recall"
    aliases = ["return"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        return_location = caller.db.book_return_location

        if not return_location:
            caller.msg("You have nowhere to recall to.")
            return

        caller.msg(
            "The world around you shimmers and fades. The smell of "
            "old paper and furniture polish fills your nostrils as "
            "the library materialises around you."
        )
        caller.move_to(return_location, quiet=True)
        caller.db.book_return_location = None
        caller.msg(caller.at_look(return_location))

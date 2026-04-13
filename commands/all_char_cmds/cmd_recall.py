"""
CmdRecall — return to the library from a book zone.

Teleports the player back to the room they were in when they read a
library book. Clears the saved return location after use. Flavour
text is paced over a couple of seconds, with movement locked while
the recall is in progress.

Usage:
    recall
"""

from evennia import Command
from evennia.utils import delay

from commands.command import FCMCommandMixin


PARAGRAPH_PAUSE = 1.0

RECALL_PARAGRAPHS = (
    "The world around you shimmers and fades.",
    "Familiar surroundings press in around you.",
    "You are back where you started.",
)


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

        if caller.ndb.book_transport:
            caller.msg("You are already recalling.")
            return

        return_location = caller.db.book_return_location
        if not return_location:
            caller.msg("You have nowhere to recall to.")
            return

        caller.ndb.book_transport = True

        caller.msg(f"\n{RECALL_PARAGRAPHS[0]}\n")
        for i, paragraph in enumerate(RECALL_PARAGRAPHS[1:], start=1):
            delay(PARAGRAPH_PAUSE * i, self._show_paragraph, caller, paragraph)

        delay(
            PARAGRAPH_PAUSE * len(RECALL_PARAGRAPHS),
            self._transport,
            caller,
            return_location,
        )

    @staticmethod
    def _show_paragraph(caller, paragraph):
        if not caller.ndb.book_transport:
            return
        caller.msg(f"{paragraph}\n")

    @staticmethod
    def _transport(caller, destination):
        caller.ndb.book_transport = False
        if not caller.location:
            return
        caller.move_to(destination, quiet=True, move_type="teleport")
        caller.db.book_return_location = None

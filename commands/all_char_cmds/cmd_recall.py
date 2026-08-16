"""
CmdRecall — return to the library from a book zone.

Teleports the player back to the room they were in when they read a
library book. Clears the saved return location after use. Flavour
text is paced over a couple of seconds on the busy lock, so movement
and every other action are refused while the recall is in progress.

Usage:
    recall
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.busy import check_busy, start_busy_ticks


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
    aliases = []
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller

        if check_busy(caller):
            return

        return_location = caller.db.book_return_location
        if not return_location:
            caller.msg("You have nowhere to recall to.")
            return

        def _paragraph(step, total):
            # A blank line opens the passage, then one line per tick.
            return (f"\n{RECALL_PARAGRAPHS[step]}\n" if step == 0
                    else f"{RECALL_PARAGRAPHS[step]}\n")

        start_busy_ticks(
            caller,
            len(RECALL_PARAGRAPHS),
            PARAGRAPH_PAUSE,
            lambda: self._transport(caller, return_location),
            progress=_paragraph,
            busy_msg="You are already recalling.",
            busy_move_msg="The world is fading around you — you can't move.",
        )

    @staticmethod
    def _transport(caller, destination):
        if not caller.location:
            return
        followers = caller.get_followers(same_room=True)
        caller.move_to(destination, quiet=True, move_type="teleport")
        for follower in followers:
            follower.move_to(destination, quiet=True, move_type="teleport")
        caller.db.book_return_location = None

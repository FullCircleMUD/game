"""
CmdRead — read a library book and get transported to its themed zone.

Searches the current room for a LibraryBook matching the player's
argument. If found, shows the book's description text (paragraph by
paragraph with a 1-second pause between each) and teleports the player
to the book's destination zone. Saves the current room as the player's
recall location.

While reading, the player is held by the busy lock — movement and any
other action are refused until the transport completes, in the book's
own wording rather than the generic "in the middle of a job".

Usage:
    read <book name>

Example:
    read winnie the pooh
"""

import re

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.world_objects.library_book import LibraryBook
from utils.busy import check_busy, start_busy_ticks
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see, p_same_height
from utils.visibility import looker_is_blind


PARAGRAPH_PAUSE = 1.0

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_paragraphs(text):
    """Split flavour text into paragraphs.

    Prefers explicit ``\\n\\n`` paragraph breaks. If none are present,
    falls back to splitting on sentence boundaries so older books
    (authored as a single string) still pace nicely.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        return paragraphs
    if not paragraphs:
        return []
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(paragraphs[0]) if s.strip()]
    return sentences or paragraphs


class CmdRead(FCMCommandMixin, Command):
    """
    Read a book in the library.

    Usage:
        read <book name>

    Reading a library book transports you into the world of the story.
    Use |wrecall|n to return to the library when you're done.
    """

    key = "read"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Read what? Usage: |wread <book name>|n")
            return

        if check_busy(caller):
            return

        room = caller.location
        if not room:
            return

        query = self.args.strip()

        # Reading is the one thing that has no version done by touch, so
        # this refuses rather than costing time. Name what they asked for
        # — "you don't see that here" reads as absent when the book is on
        # the shelf in front of them.
        if looker_is_blind(caller):
            caller.msg(f"It's too dark to read '{query}'.")
            return

        # Broad targeting — find whatever the player named in the room
        book, _ = resolve_target(
            caller, query, "items_room_fixed_nonexit",
            extra_predicates=(p_can_see,),
        )
        if not book:
            caller.msg("You don't see that here.")
            return
        if not p_same_height(caller)(book, caller):
            caller.msg(f"{book.key} is out of reach.")
            return
        if not isinstance(book, LibraryBook):
            caller.msg("That's not something you can read.")
            return

        destination = book.book_destination
        if not destination:
            caller.msg(
                "The pages are blank. This book doesn't seem to lead anywhere."
            )
            return

        desc = book.book_description or ""
        paragraphs = _split_paragraphs(desc)

        caller.db.book_return_location = room

        if not paragraphs:
            self._transport(caller, destination)
            return

        def _paragraph(step, total):
            # A blank line opens the passage, then one paragraph per tick.
            return f"\n{paragraphs[step]}\n" if step == 0 else f"{paragraphs[step]}\n"

        start_busy_ticks(
            caller,
            len(paragraphs),
            PARAGRAPH_PAUSE,
            lambda: self._transport(caller, destination),
            progress=_paragraph,
            busy_msg="You are already lost in a book.",
            busy_move_msg="You are lost in a book and can't move.",
        )

    @staticmethod
    def _transport(caller, destination):
        if not caller.location:
            return
        followers = caller.get_followers(same_room=True)
        caller.move_to(destination, quiet=True, move_type="teleport")
        for follower in followers:
            follower.move_to(destination, quiet=True, move_type="teleport")

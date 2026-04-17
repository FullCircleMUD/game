"""
CmdRead — read a library book and get transported to its themed zone.

Searches the current room for a LibraryBook matching the player's
argument. If found, shows the book's description text (paragraph by
paragraph with a 1-second pause between each) and teleports the player
to the book's destination zone. Saves the current room as the player's
recall location.

While reading, the player is locked in place — movement and re-reading
are blocked until the transport completes.

Usage:
    read <book name>

Example:
    read winnie the pooh
"""

import re

from evennia import Command
from evennia.utils import delay

from commands.command import FCMCommandMixin
from typeclasses.world_objects.library_book import LibraryBook
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see, p_same_height


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

        if caller.ndb.book_transport:
            caller.msg("You are already lost in a book.")
            return

        room = caller.location
        if not room:
            return

        # Darkness — can't read without sight
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        # Broad targeting — find whatever the player named in the room
        book, _ = resolve_target(
            caller, self.args.strip(), "items_room_fixed_nonexit",
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
        caller.ndb.book_transport = True

        if not paragraphs:
            self._transport(caller, destination)
            return

        caller.msg(f"\n{paragraphs[0]}\n")
        for i, paragraph in enumerate(paragraphs[1:], start=1):
            delay(PARAGRAPH_PAUSE * i, self._show_paragraph, caller, paragraph)

        delay(
            PARAGRAPH_PAUSE * len(paragraphs),
            self._transport,
            caller,
            destination,
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
        followers = caller.get_followers(same_room=True)
        caller.move_to(destination, quiet=True, move_type="teleport")
        for follower in followers:
            follower.move_to(destination, quiet=True, move_type="teleport")

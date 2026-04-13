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

        target = caller.search(
            self.args.strip(),
            location=room,
            typeclass="typeclasses.world_objects.library_book.LibraryBook",
            quiet=True,
        )

        if not target:
            general = caller.search(self.args.strip(), location=room, quiet=True)
            if general:
                caller.msg("That's not something you can read.")
            else:
                caller.msg("You don't see that here.")
            return

        book = target[0] if isinstance(target, list) else target

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

"""
CmdRead — read a library book and get transported to its themed zone.

Searches the current room for a LibraryBook matching the player's
argument. If found, shows the book's description text and teleports
the player to the book's destination zone. Saves the current room
as the player's recall location.

Usage:
    read <book name>

Example:
    read winnie the pooh
"""

from evennia import Command

from commands.command import FCMCommandMixin


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

        room = caller.location
        if not room:
            return

        # Search for a LibraryBook in the room
        target = caller.search(
            self.args.strip(),
            location=room,
            typeclass="typeclasses.world_objects.library_book.LibraryBook",
            quiet=True,
        )

        if not target:
            # Try a general search for better error messages
            general = caller.search(self.args.strip(), location=room, quiet=True)
            if general:
                caller.msg("That's not something you can read.")
            else:
                caller.msg("You don't see that here.")
            return

        book = target[0] if isinstance(target, list) else target

        # Check destination is set
        destination = book.book_destination
        if not destination:
            caller.msg(
                "The pages are blank. This book doesn't seem to lead anywhere."
            )
            return

        # Show the book description
        desc = book.book_description
        if desc:
            caller.msg(f"\n{desc}\n")

        # Save return location
        caller.db.book_return_location = room

        # Transport
        caller.move_to(destination, quiet=True)
        caller.msg(caller.at_look(destination))

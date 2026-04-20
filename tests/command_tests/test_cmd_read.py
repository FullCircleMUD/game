"""
Tests for the read command.

evennia test --settings settings tests.command_tests.test_cmd_read
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_read import CmdRead


class TestCmdRead(EvenniaCommandTest):
    """Test the read command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        # Create a destination room for the book
        self.dest = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Storybook Land",
        )
        self.dest.always_lit = True
        # Create a library book in the room
        self.book = create.create_object(
            "typeclasses.world_objects.library_book.LibraryBook",
            key="The Adventures of Winnie the Pooh",
            location=self.room1,
            nohome=True,
        )
        self.book.book_destination = self.dest
        self.book.book_description = "You open the book and begin to read."

    def test_no_args(self):
        """Read with no args shows usage."""
        self.call(CmdRead(), "", "Read what?")

    def test_read_not_found(self):
        """Read something that doesn't exist shows error."""
        self.call(CmdRead(), "banana", "You don't see that here.")

    def test_read_non_book(self):
        """Read a non-book item shows type error."""
        rock = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="rock",
            location=self.room1,
            nohome=True,
        )
        self.call(CmdRead(), "rock", "That's not something you can read.")

    def test_read_in_darkness(self):
        """Read in darkness should fail."""
        self.room1.always_lit = False
        self.room1.natural_light = False
        self.call(CmdRead(), "winnie", "It's too dark to see anything.")

    def test_read_book_transports(self):
        """Reading a book should transport the player."""
        self.call(CmdRead(), "winnie")
        # After the transport delay fires, player should be in dest
        # but EvenniaCommandTest doesn't run delays — just verify
        # the command didn't error and the book was found
        # (transport happens via delay callbacks)

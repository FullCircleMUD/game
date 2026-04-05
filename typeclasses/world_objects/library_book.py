"""
LibraryBook — a readable book that transports players to themed zones.

A non-takeable fixture placed in library rooms. When a player uses
``read <book>``, they see flavour text and are transported to the
book's destination zone. ``recall`` returns them to the library room
they entered from.

Usage (build script)::

    book = create_object(
        "typeclasses.world_objects.library_book.LibraryBook",
        key="Winnie the Pooh",
        location=rooms["library_children"],
    )
    book.book_description = (
        "You open the worn, honey-stained cover and begin to read. "
        "The words blur and swirl before your eyes..."
    )
    book.book_destination = hundred_acre_wood_entry_room
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.world_objects.base_fixture import WorldFixture


class LibraryBook(WorldFixture):
    """
    A library book that serves as a portal to a themed zone.

    Inherits from WorldFixture — cannot be picked up, supports
    hidden/invisible states. The ``read`` command finds these objects
    by checking for the ``book_destination`` attribute.
    """

    book_description = AttributeProperty("")
    """Flavour text shown when the player reads the book, before transport."""

    book_destination = AttributeProperty(None)
    """The entry room of the book's zone. Set to a room object or dbref."""

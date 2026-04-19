"""
FountainFixture — a permanent water source in the world.

Covers any flavour of water source: town fountains, wells, streams,
springs, waterfalls, cisterns, etc. The key, aliases, and description
are set per-instance at creation time so a single class works for all.

The ``refill`` command finds these in the room via
``is_water_source = True``.

Example builder usage::

    create_object(
        FountainFixture,
        key="a babbling creek",
        aliases=["creek", "stream", "water"],
        location=room,
        nohome=True,
    )
    obj.db.desc = "A shallow creek flows over smooth stones..."
"""

from evennia import AttributeProperty

from enums.size import Size
from typeclasses.world_objects.base_fixture import WorldFixture


class FountainFixture(WorldFixture):
    """
    Permanent world water source. Free, infinite, no state.
    """

    size = AttributeProperty(Size.LARGE.value)
    is_water_source = True

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("water_source", category="fixture_type")
        if not self.db.desc:
            self.db.desc = (
                "A source of fresh water. "
                "You could refill a water container here."
            )

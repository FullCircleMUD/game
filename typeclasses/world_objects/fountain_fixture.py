"""
FountainFixture — a permanent water source in the world.

Used for town fountains, public wells, and any other fixture that lets
players refill their water containers. The `refill` command finds these
in the room via `is_water_source = True`.

Builders create them with:
    @create/drop a stone fountain:typeclasses.world_objects.fountain_fixture.FountainFixture

Future natural water sources (rivers, wells, springs) can either be
FountainFixture instances or any other fixture that exposes
`is_water_source = True`. The command surface only checks the marker.
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
                "A stone fountain bubbles with clear, cold water. "
                "You could refill a water container here."
            )

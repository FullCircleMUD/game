"""
LitFixture — a permanent, immovable light source in the world.

Used for lamp posts, wall sconces, braziers, campfires, and any other
fixture that provides constant illumination. Always lit, infinite fuel,
cannot be picked up.

Builders create them with:
    @create/drop lamppost:typeclasses.world_objects.lit_fixture.LitFixture

The room's is_dark() check detects these via is_light_source + is_lit.
"""

from typeclasses.mixins.light_source import LightSourceMixin
from typeclasses.world_objects.base_fixture import WorldFixture


class LitFixture(LightSourceMixin, WorldFixture):
    """
    Permanent world light source. Always lit, infinite fuel.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.at_light_init()
        self.is_lit = True
        self.fuel_remaining = -1  # infinite
        self.max_fuel = -1

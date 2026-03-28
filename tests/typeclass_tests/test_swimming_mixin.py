"""
Tests for SwimmingMixin — innate aquatic movement via WATER_BREATHING.

evennia test --settings settings tests.typeclass_tests.test_swimming_mixin
"""

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.swimming_mixin import SwimmingMixin


class SwimmingTestMob(SwimmingMixin, AggressiveMob):
    """Test-only swimming mob class."""
    preferred_depth = AttributeProperty(-1)


class TestSwimmingMixin(EvenniaTest):
    """Test SwimmingMixin on a mob that composes it in."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Set room to allow depth
        self.room1.max_depth = -3
        self.mob = create.create_object(
            SwimmingTestMob,
            key="test shark",
            location=self.room1,
        )
        self.mob.is_alive = True
        self.mob.hp = 10

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        super().tearDown()

    def test_water_breathing_granted(self):
        """SwimmingMixin should grant WATER_BREATHING at creation."""
        self.assertTrue(self.mob.has_condition(Condition.WATER_BREATHING))

    def test_initial_depth_set(self):
        """room_vertical_position should be set to preferred_depth."""
        self.assertEqual(self.mob.room_vertical_position, -1)

    def test_can_swim_flag(self):
        """can_swim attribute should be True."""
        self.assertTrue(self.mob.can_swim)

    def test_dive(self):
        """dive() should decrease vertical position (go deeper)."""
        self.assertTrue(self.mob.dive())
        self.assertEqual(self.mob.room_vertical_position, -2)

    def test_dive_capped(self):
        """dive() should not exceed room max_depth."""
        self.mob.room_vertical_position = -2
        self.mob.dive(5)
        self.assertEqual(self.mob.room_vertical_position, -3)

    def test_surface(self):
        """surface() should increase vertical position (toward 0)."""
        self.assertTrue(self.mob.surface())
        self.assertEqual(self.mob.room_vertical_position, 0)

    def test_surface_capped(self):
        """surface() should not go above 0."""
        self.mob.room_vertical_position = 0
        self.assertFalse(self.mob.surface())
        self.assertEqual(self.mob.room_vertical_position, 0)

    def test_height_matching_underwater(self):
        """AggressiveMixin._try_match_height should work for swimming mobs."""
        # Target is at depth -2, mob is at -1
        self.char1.room_vertical_position = -2
        result = self.mob._try_match_height(self.char1)
        self.assertTrue(result)
        self.assertEqual(self.mob.room_vertical_position, -2)

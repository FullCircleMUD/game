"""
Tests for FlyingMixin — innate flight via Condition.FLY integration.

evennia test --settings settings tests.typeclass_tests.test_flying_mixin
"""

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.flying_mixin import FlyingMixin


class FlyingTestMob(FlyingMixin, AggressiveMob):
    """Test-only flying mob class."""
    preferred_height = AttributeProperty(1)


class TestFlyingMixin(EvenniaTest):
    """Test FlyingMixin on a mob that composes it in."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            FlyingTestMob,
            key="test crow",
            location=self.room1,
        )
        self.mob.is_alive = True
        self.mob.hp = 10

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        super().tearDown()

    def test_fly_condition_granted(self):
        """FlyingMixin should grant FLY condition at creation."""
        self.assertTrue(self.mob.has_condition(Condition.FLY))

    def test_initial_height_set(self):
        """room_vertical_position should be set to preferred_height."""
        self.assertEqual(self.mob.room_vertical_position, 1)

    def test_can_fly_flag(self):
        """can_fly attribute should be True."""
        self.assertTrue(self.mob.can_fly)

    def test_ascend(self):
        """ascend() should increase vertical position."""
        # room_base default max_height is 1, mob starts at 1 — can't ascend
        self.assertFalse(self.mob.ascend())
        # Lower first, then ascend
        self.mob.room_vertical_position = 0
        self.assertTrue(self.mob.ascend())
        self.assertEqual(self.mob.room_vertical_position, 1)

    def test_ascend_capped(self):
        """ascend() should not exceed room max_height."""
        self.mob.room_vertical_position = 0
        # room_base has max_height=1
        self.mob.ascend(5)
        self.assertEqual(self.mob.room_vertical_position, 1)

    def test_descend(self):
        """descend() should decrease vertical position."""
        self.assertTrue(self.mob.descend())
        self.assertEqual(self.mob.room_vertical_position, 0)

    def test_descend_floor(self):
        """descend() should not go below 0."""
        self.mob.room_vertical_position = 0
        self.assertFalse(self.mob.descend())
        self.assertEqual(self.mob.room_vertical_position, 0)

    def test_height_matching_works(self):
        """AggressiveMixin._try_match_height should work for flying mobs."""
        # Target is at ground level, mob is at height 1
        self.char1.room_vertical_position = 0
        result = self.mob._try_match_height(self.char1)
        self.assertTrue(result)
        self.assertEqual(self.mob.room_vertical_position, 0)

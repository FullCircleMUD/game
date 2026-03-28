"""
Tests for ClimbableMixin — climbable fixture and fall safety.

evennia test --settings settings tests.typeclass_tests.test_climbable_mixin
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class TestClimbableFixtureAttributes(EvenniaTest):
    """ClimbableFixture should have climbable data attributes."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.fixture = create.create_object(
            "typeclasses.world_objects.climbable_fixture.ClimbableFixture",
            key="a ladder",
            location=self.room1,
        )
        self.fixture.climbable_heights = {0, 1}
        self.fixture.climb_dc = 0

    def test_climbable_heights_set(self):
        self.assertEqual(self.fixture.climbable_heights, {0, 1})

    def test_climb_dc_default(self):
        self.assertEqual(self.fixture.climb_dc, 0)

    def test_climb_up_msg_default(self):
        self.assertEqual(self.fixture.climb_up_msg, "You climb upwards.")

    def test_cannot_pick_up(self):
        """Fixture should be immovable."""
        self.assertFalse(self.fixture.at_pre_get(self.char1))


class TestFallSafetyWithClimbable(EvenniaTest):
    """_check_fall() should not deal damage when a climbable fixture
    supports the character's current height."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.fixture = create.create_object(
            "typeclasses.world_objects.climbable_fixture.ClimbableFixture",
            key="a drainpipe",
            location=self.room1,
        )
        self.fixture.climbable_heights = {0, 1}
        self.char1.room_vertical_position = 1
        self.char1.hp = 100
        self.char1.hp_max = 100

    def test_safe_slide_no_damage(self):
        """Fall with climbable at height should slide safely, no damage."""
        self.char1._check_fall()
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertEqual(self.char1.hp, 100)

    def test_normal_fall_without_fixture(self):
        """Fall without climbable fixture should deal damage."""
        self.fixture.delete()
        self.char1._check_fall()
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertLess(self.char1.hp, 100)

    def test_fall_fixture_wrong_height(self):
        """Fall at height 2 with fixture supporting {0,1} should deal damage."""
        self.char1.room_vertical_position = 2
        self.room1.max_height = 2
        self.char1._check_fall()
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertLess(self.char1.hp, 100)

    def test_fly_removal_triggers_safe_slide(self):
        """Removing FLY condition while at height 1 with fixture = safe."""
        self.char1.add_condition(Condition.FLY)
        self.char1.room_vertical_position = 1
        self.char1.remove_condition(Condition.FLY)
        self.assertEqual(self.char1.room_vertical_position, 0)
        self.assertEqual(self.char1.hp, 100)

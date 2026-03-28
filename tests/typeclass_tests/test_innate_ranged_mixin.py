"""
Tests for InnateRangedMixin — innate ranged attacks for non-humanoid mobs.

evennia test --settings settings tests.typeclass_tests.test_innate_ranged_mixin
"""

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from combat.height_utils import can_reach_target, get_height_hit_modifier
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.flying_mixin import FlyingMixin
from typeclasses.mixins.innate_ranged_mixin import InnateRangedMixin


class RangedFlyingTestMob(InnateRangedMixin, FlyingMixin, AggressiveMob):
    """Test-only flying + innate ranged mob (dragon-like)."""
    preferred_height = AttributeProperty(2)
    innate_ranged_message = AttributeProperty("breathes fire at")
    damage_dice = AttributeProperty("3d8")


class RangedLimitedTestMob(InnateRangedMixin, AggressiveMob):
    """Test-only ranged mob with limited range."""
    innate_ranged_range = AttributeProperty(1)


class TestInnateRangedReach(EvenniaTest):
    """Test can_reach_target with innate ranged mobs."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.dragon = create.create_object(
            RangedFlyingTestMob,
            key="test dragon",
            location=self.room1,
        )
        self.dragon.is_alive = True
        self.dragon.hp = 100

    def tearDown(self):
        if self.dragon.pk:
            self.dragon.delete()
        super().tearDown()

    def test_can_reach_different_height(self):
        """Innate ranged mob can attack target at different height."""
        self.dragon.room_vertical_position = 1
        self.char1.room_vertical_position = 0
        self.assertTrue(can_reach_target(self.dragon, self.char1, None))

    def test_can_reach_same_height(self):
        """Same height always works."""
        self.dragon.room_vertical_position = 0
        self.char1.room_vertical_position = 0
        self.assertTrue(can_reach_target(self.dragon, self.char1, None))

    def test_mob_weapon_type_set(self):
        """InnateRangedMixin sets mob_weapon_type to missile."""
        self.assertEqual(self.dragon.mob_weapon_type, "missile")

    def test_hit_modifier_at_distance(self):
        """No penalty for innate ranged at different height."""
        self.dragon.room_vertical_position = 1
        self.char1.room_vertical_position = 0
        self.assertEqual(
            get_height_hit_modifier(self.dragon, self.char1, None), 0
        )

    def test_hit_modifier_at_melee_range(self):
        """Innate ranged at same height gets -4 penalty."""
        self.dragon.room_vertical_position = 0
        self.char1.room_vertical_position = 0
        self.assertEqual(
            get_height_hit_modifier(self.dragon, self.char1, None), -4
        )


class TestInnateRangedRangeLimit(EvenniaTest):
    """Test innate_ranged_range limiting."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            RangedLimitedTestMob,
            key="test spitter",
            location=self.room1,
        )
        self.mob.is_alive = True
        self.mob.hp = 10

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        super().tearDown()

    def test_within_range(self):
        """Can reach target within innate_ranged_range."""
        self.mob.room_vertical_position = 0
        self.char1.room_vertical_position = 1
        self.assertTrue(can_reach_target(self.mob, self.char1, None))

    def test_beyond_range(self):
        """Cannot reach target beyond innate_ranged_range."""
        self.mob.room_vertical_position = 0
        self.char1.room_vertical_position = 2
        self.assertFalse(can_reach_target(self.mob, self.char1, None))


class TestNonRangedMobBlocked(EvenniaTest):
    """Verify non-ranged mobs are still blocked by height."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob = create.create_object(
            AggressiveMob,
            key="test wolf",
            location=self.room1,
        )
        self.mob.is_alive = True
        self.mob.hp = 10

    def tearDown(self):
        if self.mob.pk:
            self.mob.delete()
        super().tearDown()

    def test_melee_blocked_by_height(self):
        """Non-ranged mob cannot reach target at different height."""
        self.mob.room_vertical_position = 0
        self.char1.room_vertical_position = 1
        self.assertFalse(can_reach_target(self.mob, self.char1, None))

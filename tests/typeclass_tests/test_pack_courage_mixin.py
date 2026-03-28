"""
Tests for PackCourageMixin — generic pack-fighting behavior.

Uses a minimal test mob class to verify the mixin in isolation.

evennia test --settings settings tests.typeclass_tests.test_pack_courage_mixin
"""

from unittest.mock import patch

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.mob_behaviours.pack_courage_mixin import PackCourageMixin


class PackTestMob(PackCourageMixin, AggressiveMob):
    """Test-only pack mob class."""
    min_allies_to_attack = AttributeProperty(1)
    flee_message = AttributeProperty("{name} flees!")


class OtherPackMob(PackCourageMixin, AggressiveMob):
    """Different mob type — should NOT count as PackTestMob ally."""
    min_allies_to_attack = AttributeProperty(1)


class TestPackCourageHelpers(EvenniaTest):
    """Test _count_allies, _has_pack_courage, _is_cornered."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob1 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        self.mob1.is_alive = True
        self.mob1.hp = 10

    def test_count_allies_alone(self):
        """Solo mob should have 0 allies."""
        self.assertEqual(self.mob1._count_allies(), 0)

    def test_count_allies_with_friends(self):
        """Three mobs in a room — each should count 2 allies."""
        mob2 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        mob2.is_alive = True
        mob3 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        mob3.is_alive = True
        self.assertEqual(self.mob1._count_allies(), 2)
        self.assertEqual(mob2._count_allies(), 2)

    def test_dead_allies_dont_count(self):
        """Dead mobs should not count as allies."""
        mob2 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        mob2.is_alive = False
        self.assertEqual(self.mob1._count_allies(), 0)

    def test_different_type_not_allies(self):
        """A different mob type in the same room is not an ally."""
        other = create.create_object(
            OtherPackMob, key="other mob", location=self.room1,
        )
        other.is_alive = True
        self.assertEqual(self.mob1._count_allies(), 0)

    def test_has_pack_courage_true(self):
        mob2 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        mob2.is_alive = True
        self.assertTrue(self.mob1._has_pack_courage())

    def test_has_pack_courage_false(self):
        self.assertFalse(self.mob1._has_pack_courage())

    def test_is_cornered_with_exits(self):
        """Room with exits — not cornered."""
        self.mob1.tags.clear(category="mob_area")
        self.assertFalse(self.mob1._is_cornered())

    def test_is_cornered_no_exits(self):
        """Room with no exits — cornered."""
        dead_end = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Dead End",
        )
        self.mob1.location = dead_end
        self.assertTrue(self.mob1._is_cornered())


class TestPackCourageAggro(EvenniaTest):
    """Test aggro gating on pack courage."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mob1 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        self.mob1.is_alive = True
        self.mob1.hp = 10
        self.mob1.tags.clear(category="mob_area")

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_no_aggro_when_alone(self, mock_delay):
        """Solo mob should flee, not attack, on player arrival."""
        self.char1.is_pc = True
        self.mob1.at_new_arrival(self.char1)
        self.assertFalse(mock_delay.called)
        # Should have fled
        self.assertEqual(self.mob1.location, self.room2)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_aggro_with_pack(self, mock_delay):
        """Mob with ally should aggro on player arrival."""
        mob2 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        mob2.is_alive = True
        self.char1.is_pc = True
        self.mob1.at_new_arrival(self.char1)
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_cornered_fights_alone(self, mock_delay):
        """Solo mob with no exits should fight."""
        dead_end = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Dead End",
        )
        self.mob1.location = dead_end
        self.char1.is_pc = True
        self.char1.location = dead_end
        self.mob1.at_new_arrival(self.char1)
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_ai_wander_attacks_with_allies(self, mock_delay):
        """ai_wander should attack if allies present."""
        mob2 = create.create_object(
            PackTestMob, key="a pack mob", location=self.room1,
        )
        mob2.is_alive = True
        self.char1.is_pc = True
        self.char1.location = self.room1
        self.mob1.ai_wander()
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_ai_wander_flees_when_alone(self, mock_delay):
        """ai_wander should flee if alone and player present."""
        self.char1.is_pc = True
        self.char1.location = self.room1
        self.mob1.ai_wander()
        self.assertFalse(mock_delay.called)
        self.assertEqual(self.mob1.location, self.room2)

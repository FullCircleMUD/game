"""
Tests for Crow mob — flying pack predator.

evennia test --settings settings tests.typeclass_tests.test_crow
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition


class TestCrowStats(EvenniaTest):
    """Crow should have correct L1 fragile stats."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.crow = create.create_object(
            "typeclasses.actors.mobs.crow.Crow",
            key="a black crow",
            location=self.room1,
        )
        self.crow.is_alive = True
        self.crow.hp = 4

    def test_stats(self):
        self.assertEqual(self.crow.hp_max, 4)
        self.assertEqual(self.crow.damage_dice, "1d2")
        self.assertEqual(self.crow.level, 1)
        self.assertEqual(self.crow.base_armor_class, 13)
        self.assertEqual(self.crow.size, "tiny")

    def test_no_loot(self):
        self.assertEqual(self.crow.loot_gold_max, 0)

    def test_pack_courage_threshold(self):
        """Needs 2+ allies (3 total) to attack."""
        self.assertEqual(self.crow.min_allies_to_attack, 2)


class TestCrowFlight(EvenniaTest):
    """Crow should spawn airborne with FLY condition."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.crow = create.create_object(
            "typeclasses.actors.mobs.crow.Crow",
            key="a black crow",
            location=self.room1,
        )
        self.crow.is_alive = True
        self.crow.hp = 4

    def test_has_fly_condition(self):
        self.assertTrue(self.crow.has_condition(Condition.FLY))

    def test_spawns_at_preferred_height(self):
        self.assertEqual(self.crow.room_vertical_position, 1)

    def test_reascends_when_idle(self):
        """Crow at ground level with no threats should re-ascend."""
        self.crow.room_vertical_position = 0
        # No combat, no players in room
        self.crow.ai_wander()
        self.assertEqual(self.crow.room_vertical_position, 1)

    def test_stays_grounded_during_combat(self):
        """Crow in combat should not re-ascend during ai_wander."""
        self.crow.room_vertical_position = 0
        # Simulate active combat handler
        self.crow.scripts.get = MagicMock(return_value=[True])
        self.crow.ai_wander()
        # Should still be at ground level — combat prevents re-ascend
        self.assertEqual(self.crow.room_vertical_position, 0)


class TestCrowPackBehavior(EvenniaTest):
    """Crow pack courage — inherited from PackCourageMixin."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.crow1 = create.create_object(
            "typeclasses.actors.mobs.crow.Crow",
            key="a black crow",
            location=self.room1,
        )
        self.crow1.is_alive = True
        self.crow1.hp = 4
        self.crow1.tags.clear(category="mob_area")

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_no_aggro_with_one_ally(self, mock_delay):
        """Two crows (needs 3) should not aggro."""
        crow2 = create.create_object(
            "typeclasses.actors.mobs.crow.Crow",
            key="a black crow",
            location=self.room1,
        )
        crow2.is_alive = True
        self.char1.is_pc = True
        self.crow1.at_new_arrival(self.char1)
        self.assertFalse(mock_delay.called)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_aggro_with_two_allies(self, mock_delay):
        """Three crows should have courage to attack."""
        for _ in range(2):
            c = create.create_object(
                "typeclasses.actors.mobs.crow.Crow",
                key="a black crow",
                location=self.room1,
            )
            c.is_alive = True
        self.char1.is_pc = True
        self.crow1.at_new_arrival(self.char1)
        self.assertTrue(mock_delay.called)

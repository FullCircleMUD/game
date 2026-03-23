"""
Tests for Kobold mob — pack courage, fleeing, and cornered behavior.

evennia test --settings settings tests.typeclass_tests.test_kobold
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestKoboldPackCourage(EvenniaTest):
    """Kobolds should only fight when allies are present or cornered."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.kobold1 = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room1,
        )
        self.kobold1.is_alive = True
        self.kobold1.hp = 14
        self.kobold1.tags.clear(category="mob_area")  # allow free movement in tests

    def test_kobold_stats(self):
        self.assertEqual(self.kobold1.hp_max, 14)
        self.assertEqual(self.kobold1.damage_dice, "1d4")
        self.assertEqual(self.kobold1.level, 2)
        self.assertEqual(self.kobold1.size, "small")

    def test_has_pack_courage_with_ally(self):
        """Kobold with 1+ ally should have courage."""
        kobold2 = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room1,
        )
        kobold2.is_alive = True
        self.assertTrue(self.kobold1._has_pack_courage())

    def test_no_pack_courage_alone(self):
        """Solo kobold should not have courage."""
        self.assertFalse(self.kobold1._has_pack_courage())

    def test_dead_allies_dont_count(self):
        """Dead kobolds don't count as allies."""
        kobold2 = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room1,
        )
        kobold2.is_alive = False
        self.assertFalse(self.kobold1._has_pack_courage())

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_attacks_with_ally_present(self, mock_delay):
        """Kobold with ally should aggro on player arrival."""
        kobold2 = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room1,
        )
        kobold2.is_alive = True
        self.char1.is_pc = True
        self.kobold1.at_new_arrival(self.char1)
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_flees_when_alone(self, mock_delay):
        """Solo kobold should flee, not attack, when player arrives."""
        self.char1.is_pc = True
        self.kobold1.at_new_arrival(self.char1)
        # Should NOT have scheduled an attack
        self.assertFalse(mock_delay.called)
        # Should have fled to room2
        self.assertEqual(self.kobold1.location, self.room2)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_fights_when_cornered(self, mock_delay):
        """Solo kobold with no exits should fight (cornered)."""
        # Create a room with no exits
        dead_end = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Dead End",
        )
        self.kobold1.location = dead_end
        self.char1.is_pc = True
        self.char1.location = dead_end
        self.kobold1.at_new_arrival(self.char1)
        # Should attack — cornered, no exits
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_ai_wander_attacks_with_allies(self, mock_delay):
        """ai_wander should attack if allies present."""
        kobold2 = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room1,
        )
        kobold2.is_alive = True
        self.char1.is_pc = True
        self.char1.location = self.room1
        self.kobold1.ai_wander()
        self.assertTrue(mock_delay.called)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_ai_wander_flees_when_alone(self, mock_delay):
        """ai_wander should flee if alone and player present."""
        self.char1.is_pc = True
        self.char1.location = self.room1
        self.kobold1.ai_wander()
        self.assertFalse(mock_delay.called)
        self.assertEqual(self.kobold1.location, self.room2)

    def test_high_aggro_threshold(self):
        """Kobolds should retreat at 70% health, not 50%."""
        self.assertEqual(self.kobold1.aggro_hp_threshold, 0.7)

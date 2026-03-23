"""
Tests for Gnoll Warlord boss — stats, rampage, dodge, never flees.

evennia test --settings settings tests.typeclass_tests.test_gnoll_warlord
"""

import random
from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestGnollWarlordStats(EvenniaTest):
    """Gnoll Warlord should have correct L6 boss stats."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.boss = create.create_object(
            "typeclasses.actors.mobs.gnoll_warlord.GnollWarlord",
            key="the Gnoll Warlord",
            location=self.room1,
        )
        self.boss.is_alive = True
        self.boss.hp = 75

    def test_stats(self):
        self.assertEqual(self.boss.hp_max, 75)
        self.assertEqual(self.boss.damage_dice, "2d6")
        self.assertEqual(self.boss.level, 6)
        self.assertEqual(self.boss.base_armor_class, 16)
        self.assertEqual(self.boss.strength, 16)

    def test_is_unique(self):
        self.assertTrue(self.boss.is_unique)

    def test_respawn_delay(self):
        self.assertEqual(self.boss.respawn_delay, 600)

    def test_never_flees_threshold(self):
        """aggro_hp_threshold=0 means is_low_health is always False."""
        self.assertEqual(self.boss.aggro_hp_threshold, 0.0)
        self.boss.hp = 1
        self.assertFalse(self.boss.is_low_health)


class TestGnollWarlordBehavior(EvenniaTest):
    """Gnoll Warlord behavior — rampage, dodge, no wander, never retreats."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.boss = create.create_object(
            "typeclasses.actors.mobs.gnoll_warlord.GnollWarlord",
            key="the Gnoll Warlord",
            location=self.room1,
        )
        self.boss.is_alive = True
        self.boss.hp = 75
        self.boss.tags.clear(category="mob_area")

    @patch("combat.combat_utils.execute_attack")
    def test_rampage_inherited(self, mock_execute):
        """Warlord should have rampage from Gnoll parent."""
        victim = MagicMock()
        victim.is_pc = True
        victim.hp = 0

        # Only char1 in the boss's room
        self.char1.is_pc = True
        self.char1.hp = 30
        self.char1.location = self.room1
        self.char2.location = self.room2

        self.boss.at_kill(victim)
        mock_execute.assert_called_once_with(self.boss, self.char1)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_ai_wander_does_not_move(self, mock_delay):
        """Boss should scan for players but never wander."""
        self.boss.ai_wander()
        self.assertEqual(self.boss.location, self.room1)

    @patch("typeclasses.actors.mobs.aggressive_mob.delay")
    def test_ai_wander_attacks_player(self, mock_delay):
        """Boss should attack players found in room."""
        self.char1.is_pc = True
        self.char1.location = self.room1
        self.boss.ai_wander()
        self.assertTrue(mock_delay.called)

    @patch.object(random, "random", return_value=0.10)
    def test_dodge_fires(self, mock_rand):
        """at_combat_tick should dodge when random < 0.20."""
        handler = MagicMock()
        with patch.object(self.boss, "execute_cmd") as mock_cmd:
            self.boss.at_combat_tick(handler)
            mock_cmd.assert_called_once_with("dodge")

    def test_never_retreats(self):
        """Warlord should switch back to wander state, never flee."""
        self.boss.hp = 1
        self.boss.ai_retreating()
        self.assertEqual(self.boss.ai.get_state(), "wander")
        self.assertEqual(self.boss.location, self.room1)

"""
Tests for Kobold Chieftain boss — stats, dodge, rally cry, no wander.

evennia test --settings settings tests.typeclass_tests.test_kobold_chieftain
"""

import random
from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


class TestKoboldChieftainStats(EvenniaTest):
    """Kobold Chieftain should have correct L3 boss stats."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.boss = create.create_object(
            "typeclasses.actors.mobs.kobold_chieftain.KoboldChieftain",
            key="the Kobold Chieftain",
            location=self.room1,
        )
        self.boss.is_alive = True
        self.boss.hp = 28

    def test_stats(self):
        self.assertEqual(self.boss.hp_max, 28)
        self.assertEqual(self.boss.damage_dice, "1d6")
        self.assertEqual(self.boss.level, 3)
        self.assertEqual(self.boss.base_armor_class, 13)
        self.assertEqual(self.boss.size, "small")

    def test_is_aggressive(self):
        self.assertTrue(self.boss.is_aggressive_to_players)


class TestKoboldChieftainBehavior(EvenniaTest):
    """Kobold Chieftain behavior — dodge, rally, no wander."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.boss = create.create_object(
            "typeclasses.actors.mobs.kobold_chieftain.KoboldChieftain",
            key="the Kobold Chieftain",
            location=self.room1,
        )
        self.boss.is_alive = True
        self.boss.hp = 28
        self.boss.tags.clear(category="mob_area")

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_ai_wander_does_not_move(self, mock_delay):
        """Boss should scan for players but never wander to another room."""
        # No players — should not move
        self.boss.ai_wander()
        self.assertEqual(self.boss.location, self.room1)

    @patch("typeclasses.mixins.aggressive_mixin.delay")
    def test_ai_wander_attacks_player(self, mock_delay):
        """Boss should attack players found in room."""
        self.char1.location = self.room1
        self.boss.ai_wander()
        self.assertTrue(mock_delay.called)

    @patch.object(random, "random", return_value=0.10)
    def test_dodge_fires_at_20_percent(self, mock_rand):
        """at_combat_tick should dodge when random < 0.20."""
        handler = MagicMock()
        with patch.object(self.boss, "execute_cmd") as mock_cmd:
            self.boss.at_combat_tick(handler)
            mock_cmd.assert_called_once_with("dodge")

    @patch.object(random, "random", return_value=0.50)
    def test_no_dodge_above_threshold(self, mock_rand):
        """at_combat_tick should not dodge when random >= 0.20."""
        handler = MagicMock()
        with patch.object(self.boss, "execute_cmd") as mock_cmd:
            self.boss.at_combat_tick(handler)
            mock_cmd.assert_not_called()

    def test_rally_cry_fires_once(self):
        """Rally cry should trigger once when HP drops below 50%."""
        self.boss.db.has_rallied = False
        self.boss.hp = 10  # below 50% of 28
        handler = MagicMock()
        self.boss.at_combat_tick(handler)
        self.assertTrue(self.boss.db.has_rallied)

    def test_rally_cry_does_not_repeat(self):
        """Rally cry should not fire twice."""
        self.boss.db.has_rallied = True
        self.boss.hp = 10
        handler = MagicMock()
        # Should not error or re-rally
        self.boss.at_combat_tick(handler)
        self.assertTrue(self.boss.db.has_rallied)

    def test_retreat_does_not_flee(self):
        """Boss should not move when retreating — just stops attacking."""
        self.boss.hp = 5  # below 30%
        self.boss.ai_retreating()
        self.assertEqual(self.boss.location, self.room1)

    def test_rally_fires_without_any_spawn_time_reset(self):
        """A fresh mob rallies on its own — nothing has to clear the flag.

        Replaces a commented-out test for `reset_chieftain_state`, and the
        `attrs: {has_rallied: False}` YAML stamp that replaced *it*. Both
        were unnecessary: an unset attr is falsy, and a mob is deleted on
        death, so every spawn starts clean. The YAML stamp was worse than
        unnecessary — `has_rallied` has no AttributeProperty, so it never
        reached `.db` and the spawner logged a WARN on every spawn.
        """
        fresh = create.create_object(
            "typeclasses.actors.mobs.kobold_chieftain.KoboldChieftain",
            key="the Kobold Chieftain",
            location=self.room1,
        )
        self.assertFalse(fresh.db.has_rallied)

        fresh.hp = fresh.hp_max // 4  # below 50%
        fresh.at_combat_tick(None)

        self.assertTrue(fresh.db.has_rallied)

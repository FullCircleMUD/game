"""
Tests for at_gain_experience_points() — levelling, level cap, and XP loss guards.

evennia test --settings settings tests.typeclass_tests.test_experience
"""

from evennia.utils.test_resources import EvenniaTest

from utils.experience_table import EXPERIENCE_TABLE


class TestExperienceLevelling(EvenniaTest):
    """Tests for XP gain, level-up, level cap, and death XP penalty."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── Normal level-up ─────────────────────────────────────────

    def test_normal_level_up(self):
        """Gaining enough XP to cross threshold grants a level."""
        self.char1.experience_points = 0
        self.char1.total_level = 1
        self.char1.highest_xp_level_earned = 1
        self.char1.levels_to_spend = 0

        # Level 2 requires 1000 XP
        self.char1.at_gain_experience_points(1000)

        self.assertEqual(self.char1.total_level, 2)
        self.assertEqual(self.char1.levels_to_spend, 1)
        self.assertEqual(self.char1.highest_xp_level_earned, 2)

    def test_xp_below_threshold_no_level(self):
        """XP below next threshold does not grant a level."""
        self.char1.experience_points = 0
        self.char1.total_level = 1
        self.char1.highest_xp_level_earned = 1
        self.char1.levels_to_spend = 0

        self.char1.at_gain_experience_points(500)

        self.assertEqual(self.char1.total_level, 1)
        self.assertEqual(self.char1.levels_to_spend, 0)
        self.assertEqual(self.char1.experience_points, 500)

    # ── Multi-level-up ──────────────────────────────────────────

    def test_multi_level_up(self):
        """Large XP gain crossing multiple thresholds grants multiple levels."""
        self.char1.experience_points = 0
        self.char1.total_level = 1
        self.char1.highest_xp_level_earned = 1
        self.char1.levels_to_spend = 0

        # Level 2 = 1000, Level 3 = 2500, Level 4 = 4500
        self.char1.at_gain_experience_points(5000)

        self.assertEqual(self.char1.total_level, 4)
        self.assertEqual(self.char1.levels_to_spend, 3)
        self.assertEqual(self.char1.highest_xp_level_earned, 4)

    # ── Level 40 cap ────────────────────────────────────────────

    def test_level_40_cap_no_crash(self):
        """Character at level 40 gaining XP does not crash (no infinite recursion)."""
        self.char1.total_level = 40
        self.char1.highest_xp_level_earned = 40
        self.char1.levels_to_spend = 0
        self.char1.experience_points = EXPERIENCE_TABLE[40]

        # Should NOT raise RecursionError
        self.char1.at_gain_experience_points(10000)

        self.assertEqual(self.char1.total_level, 40)
        self.assertEqual(self.char1.levels_to_spend, 0)

    def test_xp_accumulates_at_cap(self):
        """XP still accumulates at level 40, just no level-up."""
        self.char1.total_level = 40
        self.char1.highest_xp_level_earned = 40
        self.char1.experience_points = EXPERIENCE_TABLE[40]

        self.char1.at_gain_experience_points(5000)

        self.assertEqual(self.char1.experience_points, EXPERIENCE_TABLE[40] + 5000)

    # ── Death XP penalty + re-earn ──────────────────────────────

    def test_death_penalty_no_duplicate_level(self):
        """After death XP loss and re-earning, no extra levels_to_spend granted."""
        # Character just reached level 5
        self.char1.total_level = 5
        self.char1.highest_xp_level_earned = 5
        self.char1.levels_to_spend = 0
        self.char1.experience_points = EXPERIENCE_TABLE[5]  # 7000

        # Simulate death: lose 5% XP
        xp_penalty = int(self.char1.experience_points * 0.05)
        self.char1.experience_points -= xp_penalty  # 6650

        # XP is now below level 5 threshold (7000) but total_level stays 5
        self.assertLess(self.char1.experience_points, EXPERIENCE_TABLE[5])
        self.assertEqual(self.char1.total_level, 5)

        # Re-earn XP past the level 5 threshold
        self.char1.at_gain_experience_points(1000)  # 7650

        # Should NOT gain an extra level — still level 5
        self.assertEqual(self.char1.total_level, 5)
        self.assertEqual(self.char1.levels_to_spend, 0)

    # ── Defensive guard ─────────────────────────────────────────

    def test_manual_level_reduction_no_duplicate_rewards(self):
        """If total_level is manually reduced, re-earning does not duplicate rewards."""
        # Character was level 5, someone manually sets total_level to 3
        self.char1.total_level = 3
        self.char1.highest_xp_level_earned = 5
        self.char1.levels_to_spend = 0
        self.char1.experience_points = EXPERIENCE_TABLE[3]  # 2500

        # Earn enough XP to cross level 4 and 5 thresholds
        self.char1.at_gain_experience_points(5000)  # 7500

        # total_level should restore to 5 (crossing thresholds 4 and 5)
        self.assertEqual(self.char1.total_level, 5)
        # But NO levels_to_spend granted — these were already earned
        self.assertEqual(self.char1.levels_to_spend, 0)

    def test_manual_level_reduction_new_thresholds_still_rewarded(self):
        """After manual reduction, genuinely NEW thresholds still grant rewards."""
        # Character was level 3, manually set to 2, then earns past level 3 AND 4
        self.char1.total_level = 2
        self.char1.highest_xp_level_earned = 3
        self.char1.levels_to_spend = 0
        self.char1.experience_points = EXPERIENCE_TABLE[2]  # 1000

        # Earn enough to reach level 5 (threshold 7000)
        self.char1.at_gain_experience_points(7000)  # 8000

        self.assertEqual(self.char1.total_level, 5)
        # Level 3 was already earned, levels 4 and 5 are NEW
        self.assertEqual(self.char1.levels_to_spend, 2)
        self.assertEqual(self.char1.highest_xp_level_earned, 5)

"""
Tests for the experience table — XP thresholds and helper functions.

Verifies the EXPERIENCE_TABLE dict structure, get_xp_for_next_level(),
and get_xp_gap() including edge cases at level boundaries.

evennia test --settings settings tests.utils_tests.test_experience_table
"""

from unittest import TestCase

from utils.experience_table import (
    EXPERIENCE_TABLE,
    get_xp_for_next_level,
    get_xp_gap,
)


class TestExperienceTable(TestCase):
    """Test the EXPERIENCE_TABLE data structure."""

    def test_has_all_40_levels(self):
        """Table should have entries for levels 1 through 40."""
        for level in range(1, 41):
            self.assertIn(level, EXPERIENCE_TABLE)

    def test_level_1_is_zero(self):
        """Level 1 requires 0 XP (starting level)."""
        self.assertEqual(EXPERIENCE_TABLE[1], 0)

    def test_level_40_is_max(self):
        """Level 40 is the maximum level."""
        self.assertEqual(EXPERIENCE_TABLE[40], 2417000)

    def test_monotonically_increasing(self):
        """Each level should require more XP than the previous one."""
        for level in range(2, 41):
            self.assertGreater(
                EXPERIENCE_TABLE[level],
                EXPERIENCE_TABLE[level - 1],
                f"Level {level} XP should be greater than level {level - 1}",
            )

    def test_no_extra_levels(self):
        """Table should have exactly 40 entries."""
        self.assertEqual(len(EXPERIENCE_TABLE), 40)


class TestGetXPForNextLevel(TestCase):
    """Test get_xp_for_next_level()."""

    def test_level_1_to_2(self):
        """Level 1 needs 1000 XP to reach level 2."""
        self.assertEqual(get_xp_for_next_level(1), 1000)

    def test_level_39_to_40(self):
        """Level 39 needs 2417000 XP to reach level 40."""
        self.assertEqual(get_xp_for_next_level(39), 2417000)

    def test_max_level_returns_zero(self):
        """Level 40 (max) should return 0."""
        self.assertEqual(get_xp_for_next_level(40), 0)

    def test_above_max_returns_zero(self):
        """Levels above 40 should also return 0."""
        self.assertEqual(get_xp_for_next_level(41), 0)
        self.assertEqual(get_xp_for_next_level(100), 0)

    def test_mid_level(self):
        """Mid-level XP threshold check."""
        self.assertEqual(get_xp_for_next_level(15), 126000)

    def test_returns_absolute_threshold(self):
        """Return value is the absolute XP needed, not the gap."""
        # get_xp_for_next_level returns EXPERIENCE_TABLE[level+1]
        for level in range(1, 40):
            self.assertEqual(
                get_xp_for_next_level(level),
                EXPERIENCE_TABLE[level + 1],
            )


class TestGetXPGap(TestCase):
    """Test get_xp_gap()."""

    def test_level_1_gap_is_zero(self):
        """Level 1 has no previous level, gap should be 0."""
        self.assertEqual(get_xp_gap(1), 0)

    def test_level_0_gap_is_zero(self):
        """Level 0 (invalid) should return 0."""
        self.assertEqual(get_xp_gap(0), 0)

    def test_negative_level_gap_is_zero(self):
        """Negative level should return 0."""
        self.assertEqual(get_xp_gap(-1), 0)

    def test_level_2_gap(self):
        """Gap from level 1 to 2 should be 1000."""
        self.assertEqual(get_xp_gap(2), 1000)

    def test_level_3_gap(self):
        """Gap from level 2 to 3 should be 1500."""
        self.assertEqual(get_xp_gap(3), 1500)

    def test_level_40_gap(self):
        """Gap from level 39 to 40."""
        self.assertEqual(get_xp_gap(40), 2417000 - 2191000)

    def test_all_gaps_positive(self):
        """All gaps (level 2-40) should be positive."""
        for level in range(2, 41):
            self.assertGreater(
                get_xp_gap(level), 0,
                f"Gap at level {level} should be positive",
            )

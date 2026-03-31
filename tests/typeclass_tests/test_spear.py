"""
Tests for SpearNFTItem — spear with reach counter mastery.

Validates:
    - No parries, no extra attacks at any mastery
    - No reach counters at UNSKILLED/BASIC/SKILLED
    - Reach counters scale with mastery (0/0/0/1/1/2)
    - weapon_type_key and tag set correctly

evennia test --settings settings tests.typeclass_tests.test_spear
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_spear(location=None):
    """Create a SpearNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.spear_nft_item.SpearNFTItem",
        key="Test Spear",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's spear mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"spear": level_int}


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestSpearMasteryOverrides(EvenniaTest):
    """Test spear mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        spear = _make_spear()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(spear.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks(self):
        spear = _make_spear()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(spear.get_extra_attacks(self.char1), 0)

    def test_no_riposte(self):
        spear = _make_spear()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertFalse(spear.has_riposte(self.char1))

    def test_weapon_type_key(self):
        spear = _make_spear()
        self.assertEqual(spear.weapon_type_key, "spear")

    def test_has_spear_tag(self):
        spear = _make_spear()
        self.assertTrue(spear.tags.has("spear", category="weapon_type"))


# ================================================================== #
#  Reach Counter Tests
# ================================================================== #

class TestSpearReachCounters(EvenniaTest):
    """Test reach counter scaling by mastery."""

    def create_script(self):
        pass

    def test_no_counters_unskilled(self):
        spear = _make_spear()
        _set_mastery(self.char1, 0)
        self.assertEqual(spear.get_reach_counters_per_round(self.char1), 0)

    def test_no_counters_basic(self):
        spear = _make_spear()
        _set_mastery(self.char1, 1)
        self.assertEqual(spear.get_reach_counters_per_round(self.char1), 0)

    def test_no_counter_skilled(self):
        spear = _make_spear()
        _set_mastery(self.char1, 2)
        self.assertEqual(spear.get_reach_counters_per_round(self.char1), 0)

    def test_one_counter_expert(self):
        spear = _make_spear()
        _set_mastery(self.char1, 3)
        self.assertEqual(spear.get_reach_counters_per_round(self.char1), 1)

    def test_one_counter_master(self):
        spear = _make_spear()
        _set_mastery(self.char1, 4)
        self.assertEqual(spear.get_reach_counters_per_round(self.char1), 1)

    def test_two_counters_gm(self):
        spear = _make_spear()
        _set_mastery(self.char1, 5)
        self.assertEqual(spear.get_reach_counters_per_round(self.char1), 2)

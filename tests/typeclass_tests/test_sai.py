"""
Tests for SaiNFTItem — parry-to-disarm specialist.

Validates:
    - Parries: 0/1/2/3/4/5
    - No parry advantage
    - No riposte
    - No extra attacks at any level
    - No off-hand attacks (parry-to-disarm, not dual-wield)
    - Disarm-on-parry mechanic not yet implemented

evennia test --settings settings tests.typeclass_tests.test_sai
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_sai():
    """Create a SaiNFTItem for testing."""
    return create.create_object(
        "typeclasses.items.weapons.sai_nft_item.SaiNFTItem",
        key="Test Sai",
        nohome=True,
    )


def _set_mastery(char, level_int):
    """Set char's sai mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"sai": level_int}


def _mock_target_weapon(weapon_type_key="long_sword", mastery_bonus=0):
    """Create a mock weapon for the target."""
    weapon = MagicMock()
    weapon.weapon_type_key = weapon_type_key
    weapon.key = "Iron Longsword"
    weapon.get_wielder_mastery.return_value = MagicMock(bonus=mastery_bonus)
    return weapon


def _mock_target(size="medium", weapon=None):
    """Create a mock target for disarm testing."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.strength = 10
    target.get_attribute_bonus.return_value = 0
    target.race = None
    target.size = size
    target.remove.return_value = (True, "Removed.")
    target.location = MagicMock()
    # If weapon provided, mock get_weapon to return it
    target._mock_weapon = weapon
    return target


def _mock_handler(disarm_checks=1):
    """Create a mock combat handler."""
    handler = MagicMock()
    handler.disarm_checks_remaining = disarm_checks
    return handler


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestSaiMasteryOverrides(EvenniaTest):
    """Test sai mastery returns."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        sai = _make_sai()
        self.assertEqual(sai.weapon_type_key, "sai")

    def test_has_sai_tag(self):
        sai = _make_sai()
        self.assertTrue(sai.tags.has("sai", category="weapon_type"))

    def test_can_dual_wield(self):
        sai = _make_sai()
        self.assertTrue(sai.can_dual_wield)

    def test_no_extra_attacks(self):
        sai = _make_sai()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_extra_attacks(self.char1), 0)

    def test_parries(self):
        sai = _make_sai()
        expected = [0, 1, 2, 3, 4, 5]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_parries_per_round(self.char1), exp,
                             f"Level {level}: expected {exp}")

    def test_no_parry_advantage(self):
        """Sai has no parry advantage at any mastery level."""
        sai = _make_sai()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertFalse(sai.get_parry_advantage(self.char1),
                             f"Level {level} should NOT have parry advantage")

    def test_no_riposte(self):
        """Sai has no riposte at any mastery level."""
        sai = _make_sai()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertFalse(sai.has_riposte(self.char1),
                             f"Level {level} should NOT have riposte")



# NOTE: TestSaiDisarm removed — the on-hit disarm mechanic was removed.
# The sai now disarms on parry, which is not yet implemented.
# Disarm-on-parry tests will be added when the mechanic is implemented.

"""
Tests for HammerNFTItem — hammer with devastating blow crit mastery.

Validates:
    - No parries, no extra attacks
    - No crit bonus at UNSKILLED/BASIC (multiplier 1.0)
    - Crit multiplier scales (1.25/1.5/1.75/2.0)
    - at_crit returns multiplied damage
    - at_hit returns damage unchanged (no on-hit mechanic)
    - weapon_type_key is set correctly

evennia test --settings settings tests.typeclass_tests.test_hammer
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_hammer(location=None):
    """Create a HammerNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.hammer_nft_item.HammerNFTItem",
        key="Test Hammer",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's hammer mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"hammer": level_int}


def _mock_target():
    """Create a mock target."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    return target


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestHammerMasteryOverrides(EvenniaTest):
    """Test hammer mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        hammer = _make_hammer()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(hammer.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks(self):
        hammer = _make_hammer()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(hammer.get_extra_attacks(self.char1), 0)

    def test_weapon_type_key(self):
        hammer = _make_hammer()
        self.assertEqual(hammer.weapon_type_key, "hammer")

    def test_has_hammer_tag(self):
        hammer = _make_hammer()
        self.assertTrue(hammer.tags.has("hammer", category="weapon_type"))


# ================================================================== #
#  Devastating Blow (Crit Multiplier) Tests
# ================================================================== #

class TestHammerDevastatingBlow(EvenniaTest):
    """Test crit damage multiplier mechanic on hammer."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.hammer = _make_hammer()

    def test_no_crit_bonus_unskilled(self):
        """UNSKILLED: multiplier 1.0 → damage unchanged."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 20, "bludgeoning")

        self.assertEqual(result, 20)

    def test_no_crit_bonus_basic(self):
        """BASIC: multiplier 1.0 → damage unchanged."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 20, "bludgeoning")

        self.assertEqual(result, 20)

    def test_crit_skilled(self):
        """SKILLED: multiplier 1.25 → 20 * 1.25 = 25."""
        _set_mastery(self.char1, 2)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 20, "bludgeoning")

        self.assertEqual(result, 25)

    def test_crit_expert(self):
        """EXPERT: multiplier 1.5 → 20 * 1.5 = 30."""
        _set_mastery(self.char1, 3)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 20, "bludgeoning")

        self.assertEqual(result, 30)

    def test_crit_master(self):
        """MASTER: multiplier 1.75 → 20 * 1.75 = 35."""
        _set_mastery(self.char1, 4)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 20, "bludgeoning")

        self.assertEqual(result, 35)

    def test_crit_gm(self):
        """GM: multiplier 2.0 → 20 * 2.0 = 40."""
        _set_mastery(self.char1, 5)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 20, "bludgeoning")

        self.assertEqual(result, 40)

    def test_crit_gm_odd_damage(self):
        """GM: multiplier 2.0 on odd damage → 15 * 2.0 = 30."""
        _set_mastery(self.char1, 5)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 15, "bludgeoning")

        self.assertEqual(result, 30)

    def test_crit_skilled_truncation(self):
        """SKILLED: 1.25 on 13 → int(16.25) = 16 (truncated)."""
        _set_mastery(self.char1, 2)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 13, "bludgeoning")

        self.assertEqual(result, 16)

    def test_crit_master_truncation(self):
        """MASTER: 1.75 on 11 → int(19.25) = 19 (truncated)."""
        _set_mastery(self.char1, 4)
        target = _mock_target()

        result = self.hammer.at_crit(self.char1, target, 11, "bludgeoning")

        self.assertEqual(result, 19)

    def test_at_hit_no_bonus(self):
        """at_hit should NOT add damage (hammer has no on-hit mechanic)."""
        _set_mastery(self.char1, 5)
        target = _mock_target()

        # at_hit is inherited from base — should pass through damage
        result = self.hammer.at_hit(self.char1, target, 42, "bludgeoning")

        self.assertEqual(result, 42)

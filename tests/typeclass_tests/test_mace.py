"""
Tests for MaceNFTItem — mace with anti-armor crush mastery.

Validates:
    - No parries, extra attacks at MASTER/GM only
    - No crush bonus at UNSKILLED/BASIC
    - Crush bonus scales with target AC above threshold (12)
    - Crush bonus capped by mastery tier
    - No bonus vs low-AC targets (unarmored)
    - weapon_type_key and tag set correctly

evennia test --settings settings tests.typeclass_tests.test_mace
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_mace(location=None):
    """Create a MaceNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.mace_nft_item.MaceNFTItem",
        key="Test Mace",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's mace mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"mace": level_int}


def _mock_target(armor_class=10):
    """Create a mock target with specific armor_class."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.armor_class = armor_class
    return target


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestMaceMasteryOverrides(EvenniaTest):
    """Test mace mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        mace = _make_mace()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(mace.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks_low_mastery(self):
        mace = _make_mace()
        for level in range(4):  # UNSKILLED through EXPERT
            _set_mastery(self.char1, level)
            self.assertEqual(mace.get_extra_attacks(self.char1), 0)

    def test_extra_attack_master(self):
        mace = _make_mace()
        _set_mastery(self.char1, 4)  # MASTER
        self.assertEqual(mace.get_extra_attacks(self.char1), 1)

    def test_extra_attack_gm(self):
        mace = _make_mace()
        _set_mastery(self.char1, 5)  # GM
        self.assertEqual(mace.get_extra_attacks(self.char1), 1)

    def test_weapon_type_key(self):
        mace = _make_mace()
        self.assertEqual(mace.weapon_type_key, "mace")

    def test_has_mace_tag(self):
        mace = _make_mace()
        self.assertTrue(mace.tags.has("mace", category="weapon_type"))


# ================================================================== #
#  Anti-Armor Crush Tests
# ================================================================== #

class TestMaceCrush(EvenniaTest):
    """Test anti-armor crush mechanic on mace."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.mace = _make_mace()

    def test_no_crush_unskilled(self):
        """UNSKILLED should never add crush bonus."""
        _set_mastery(self.char1, 0)
        target = _mock_target(armor_class=18)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 10)

    def test_no_crush_basic(self):
        """BASIC should never add crush bonus."""
        _set_mastery(self.char1, 1)
        target = _mock_target(armor_class=18)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 10)

    def test_no_crush_low_ac(self):
        """No crush bonus vs targets with AC 12 or below."""
        _set_mastery(self.char1, 5)  # GM
        target = _mock_target(armor_class=12)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 10)

    def test_no_crush_unarmored(self):
        """No crush bonus vs unarmored (AC 10)."""
        _set_mastery(self.char1, 5)  # GM
        target = _mock_target(armor_class=10)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 10)

    def test_crush_skilled_ac14(self):
        """SKILLED: AC 14 → excess 2, cap 2 → +2 bonus."""
        _set_mastery(self.char1, 2)
        target = _mock_target(armor_class=14)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 12)

    def test_crush_skilled_capped(self):
        """SKILLED: AC 18 → excess 6, but cap 2 → only +2."""
        _set_mastery(self.char1, 2)
        target = _mock_target(armor_class=18)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 12)

    def test_crush_expert_ac15(self):
        """EXPERT: AC 15 → excess 3, cap 3 → +3 bonus."""
        _set_mastery(self.char1, 3)
        target = _mock_target(armor_class=15)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 13)

    def test_crush_master_ac16(self):
        """MASTER: AC 16 → excess 4, cap 4 → +4 bonus."""
        _set_mastery(self.char1, 4)
        target = _mock_target(armor_class=16)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 14)

    def test_crush_gm_ac18(self):
        """GM: AC 18 → excess 6, cap 8 → +6 bonus."""
        _set_mastery(self.char1, 5)
        target = _mock_target(armor_class=18)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 16)

    def test_crush_gm_ac20(self):
        """GM: AC 20 → excess 8, cap 8 → +8 bonus."""
        _set_mastery(self.char1, 5)
        target = _mock_target(armor_class=20)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 18)

    def test_crush_ac13(self):
        """AC 13 → excess 1 → +1 bonus (below any cap)."""
        _set_mastery(self.char1, 5)  # GM
        target = _mock_target(armor_class=13)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 11)

    def test_crush_boundary_ac12(self):
        """AC exactly 12 → excess 0 → no bonus."""
        _set_mastery(self.char1, 5)
        target = _mock_target(armor_class=12)

        result = self.mace.at_hit(self.char1, target, 10, "bludgeoning")

        self.assertEqual(result, 10)

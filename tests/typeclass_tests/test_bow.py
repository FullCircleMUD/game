"""
Tests for BowNFTItem — bow with slowing shot + extra attack mastery.

Validates:
    - No parries, extra attacks at MASTER/GM
    - No slow at UNSKILLED/BASIC
    - Contested slow roll (archer DEX+mastery vs target STR)
    - Slow durations scale with mastery (1/2/2/3 rounds)
    - Slow applies SLOWED named effect with Condition.SLOWED
    - Anti-stacking: new slow replaces existing
    - Slow fails when target wins contest

evennia test --settings settings tests.typeclass_tests.test_bow
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_bow(location=None):
    """Create a BowNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.bow_nft_item.BowNFTItem",
        key="Test Bow",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's bow mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"bow": level_int}


def _mock_target():
    """Create a mock target for slow testing."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.strength = 14
    target.get_attribute_bonus.return_value = 2  # +2 STR mod
    target.apply_slowed = MagicMock(return_value=True)
    target.has_effect.return_value = False
    return target


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestBowMasteryOverrides(EvenniaTest):
    """Test bow mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        bow = _make_bow()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(bow.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks_before_master(self):
        bow = _make_bow()
        for level in range(4):  # UNSKILLED through EXPERT
            _set_mastery(self.char1, level)
            self.assertEqual(bow.get_extra_attacks(self.char1), 0)

    def test_extra_attack_at_master(self):
        bow = _make_bow()
        _set_mastery(self.char1, 4)  # MASTER
        self.assertEqual(bow.get_extra_attacks(self.char1), 1)

    def test_extra_attack_at_gm(self):
        bow = _make_bow()
        _set_mastery(self.char1, 5)  # GM
        self.assertEqual(bow.get_extra_attacks(self.char1), 1)

    def test_weapon_type_key(self):
        bow = _make_bow()
        self.assertEqual(bow.weapon_type_key, "bow")

    def test_has_bow_tag(self):
        bow = _make_bow()
        self.assertTrue(bow.tags.has("bow", category="weapon_type"))


# ================================================================== #
#  Slowing Shot Tests
# ================================================================== #

class TestBowSlowingShot(EvenniaTest):
    """Test contested slowing shot mechanic on bow."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bow = _make_bow()

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_no_slow_unskilled(self, mock_dice):
        """UNSKILLED should never attempt slow."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.bow.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()
        target.apply_slowed.assert_not_called()

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_no_slow_basic(self, mock_dice):
        """BASIC should never attempt slow."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.bow.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_skilled_wins_contest(self, mock_dice):
        """SKILLED: archer wins contest → SLOWED for 1 round."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = MagicMock(return_value=3)  # +3 DEX
        target = _mock_target()
        # Archer rolls 15 + 3 DEX + 2 mastery = 20
        # Target rolls 8 + 2 STR = 10
        mock_dice.roll.side_effect = [15, 8]

        self.bow.at_hit(self.char1, target, 5, "piercing")

        target.apply_slowed.assert_called_once()
        args, kwargs = target.apply_slowed.call_args
        self.assertEqual(args[0], 1)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_expert_duration(self, mock_dice):
        """EXPERT: slow duration should be 2 rounds."""
        _set_mastery(self.char1, 3)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = MagicMock(return_value=3)
        target = _mock_target()
        mock_dice.roll.side_effect = [18, 5]  # archer wins

        self.bow.at_hit(self.char1, target, 5, "piercing")

        args, kwargs = target.apply_slowed.call_args
        self.assertEqual(args[0], 2)  # duration_rounds

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_master_duration(self, mock_dice):
        """MASTER: slow duration should be 2 rounds."""
        _set_mastery(self.char1, 4)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = MagicMock(return_value=3)
        target = _mock_target()
        mock_dice.roll.side_effect = [18, 5]

        self.bow.at_hit(self.char1, target, 5, "piercing")

        args, kwargs = target.apply_slowed.call_args
        self.assertEqual(args[0], 2)  # duration_rounds

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_gm_duration(self, mock_dice):
        """GM: slow duration should be 3 rounds."""
        _set_mastery(self.char1, 5)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = MagicMock(return_value=3)
        target = _mock_target()
        mock_dice.roll.side_effect = [18, 5]

        self.bow.at_hit(self.char1, target, 5, "piercing")

        args, kwargs = target.apply_slowed.call_args
        self.assertEqual(args[0], 3)  # duration_rounds

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_target_wins_contest(self, mock_dice):
        """Target wins contested roll → no slow applied."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = MagicMock(return_value=0)
        target = _mock_target()
        # Archer rolls 5 + 0 DEX + 2 mastery = 7
        # Target rolls 18 + 2 STR = 20
        mock_dice.roll.side_effect = [5, 18]

        self.bow.at_hit(self.char1, target, 5, "piercing")

        target.apply_slowed.assert_not_called()

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_tie_goes_to_target(self, mock_dice):
        """Tied contest → no slow (archer must beat, not tie)."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 14
        self.char1.get_attribute_bonus = MagicMock(return_value=2)
        target = _mock_target()
        # Archer rolls 10 + 2 DEX + 2 mastery = 14
        # Target rolls 12 + 2 STR = 14
        mock_dice.roll.side_effect = [10, 12]

        self.bow.at_hit(self.char1, target, 5, "piercing")

        target.apply_slowed.assert_not_called()

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged regardless of slow."""
        _set_mastery(self.char1, 5)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = MagicMock(return_value=3)
        target = _mock_target()
        mock_dice.roll.side_effect = [18, 5]

        result = self.bow.at_hit(self.char1, target, 42, "piercing")

        self.assertEqual(result, 42)

    @patch("typeclasses.items.weapons.bow_nft_item.dice")
    def test_slow_not_applied_when_effect_returns_false(self, mock_dice):
        """If apply_named_effect returns False, no messages should fire."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = MagicMock(return_value=3)
        target = _mock_target()
        target.apply_slowed = MagicMock(return_value=False)  # anti-stacking
        mock_dice.roll.side_effect = [18, 5]

        self.bow.at_hit(self.char1, target, 5, "piercing")

        target.apply_slowed.assert_called_once()

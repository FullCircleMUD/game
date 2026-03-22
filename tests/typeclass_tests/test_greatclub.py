"""
Tests for GreatclubNFTItem — two-handed greatclub with heavy stagger mastery.

Validates:
    - No parries, no extra attacks
    - Two-handed
    - No stagger at UNSKILLED/BASIC
    - Stagger chance scales (15/20/25/30%)
    - Hit penalty scales (-3 at SKILLED/EXPERT, -4 at MASTER/GM)
    - Duration scales (1 round at SKILLED/EXPERT, 2 rounds at MASTER/GM)
    - Anti-stacking: already-staggered targets skipped
    - Boundary tests for d100 roll
    - weapon_type_key is set correctly

evennia test --settings settings tests.typeclass_tests.test_greatclub
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_greatclub(location=None):
    """Create a GreatclubNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.greatclub_nft_item.GreatclubNFTItem",
        key="Test Greatclub",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's greatclub mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"greatclub": level_int}


def _mock_target(already_staggered=False):
    """Create a mock target for stagger testing."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.has_effect.return_value = already_staggered
    target.apply_staggered = MagicMock(return_value=True)
    return target


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestGreatclubMasteryOverrides(EvenniaTest):
    """Test greatclub mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        gc = _make_greatclub()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(gc.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks(self):
        gc = _make_greatclub()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(gc.get_extra_attacks(self.char1), 0)

    def test_two_handed(self):
        gc = _make_greatclub()
        self.assertTrue(gc.two_handed)

    def test_weapon_type_key(self):
        gc = _make_greatclub()
        self.assertEqual(gc.weapon_type_key, "greatclub")

    def test_has_greatclub_tag(self):
        gc = _make_greatclub()
        self.assertTrue(gc.tags.has("greatclub", category="weapon_type"))


# ================================================================== #
#  Heavy Stagger Tests
# ================================================================== #

class TestGreatclubStagger(EvenniaTest):
    """Test heavy stagger mechanic on greatclub."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.gc = _make_greatclub()

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_no_stagger_unskilled(self, mock_dice):
        """UNSKILLED should never attempt stagger."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()
        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_no_stagger_basic(self, mock_dice):
        """BASIC should never attempt stagger."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_skilled_hit(self, mock_dice):
        """SKILLED: d100=12 <= 15% → stagger applied with -3 penalty."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 12

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()
        args, kwargs = target.apply_staggered.call_args
        self.assertEqual(args[0], -3)  # hit_penalty
        self.assertEqual(args[1], 1)   # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_skilled_miss(self, mock_dice):
        """SKILLED: d100=20 > 15% → no stagger."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 20

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_expert(self, mock_dice):
        """EXPERT: d100=18 <= 20% → stagger with -3, 1 round."""
        _set_mastery(self.char1, 3)
        target = _mock_target()
        mock_dice.roll.return_value = 18

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()
        args, kwargs = target.apply_staggered.call_args
        self.assertEqual(args[0], -3)  # hit_penalty
        self.assertEqual(args[1], 1)   # duration_rounds

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_master(self, mock_dice):
        """MASTER: d100=22 <= 25% → stagger with -4, 2 rounds."""
        _set_mastery(self.char1, 4)
        target = _mock_target()
        mock_dice.roll.return_value = 22

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()
        args, kwargs = target.apply_staggered.call_args
        self.assertEqual(args[0], -4)  # hit_penalty
        self.assertEqual(args[1], 2)   # duration_rounds

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_gm(self, mock_dice):
        """GM: d100=28 <= 30% → stagger with -4, 2 rounds."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 28

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()
        args, kwargs = target.apply_staggered.call_args
        self.assertEqual(args[0], -4)  # hit_penalty
        self.assertEqual(args[1], 2)   # duration_rounds

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_boundary_passes(self, mock_dice):
        """d100 exactly equal to chance should pass."""
        _set_mastery(self.char1, 2)  # SKILLED: 15%
        target = _mock_target()
        mock_dice.roll.return_value = 15

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_boundary_fails(self, mock_dice):
        """d100 one above chance should fail."""
        _set_mastery(self.char1, 2)  # SKILLED: 15%
        target = _mock_target()
        mock_dice.roll.return_value = 16

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_skip_already_staggered(self, mock_dice):
        """Already-staggered targets should not be staggered again."""
        _set_mastery(self.char1, 5)
        target = _mock_target(already_staggered=True)
        mock_dice.roll.return_value = 1

        self.gc.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.greatclub_nft_item.dice")
    def test_stagger_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged (stagger is side effect)."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 1

        result = self.gc.at_hit(self.char1, target, 42, "bludgeoning")

        self.assertEqual(result, 42)

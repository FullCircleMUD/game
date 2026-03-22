"""
Tests for ClubNFTItem — club with light stagger mastery.

Validates:
    - No parries, extra attacks at MASTER/GM only
    - No stagger at UNSKILLED/BASIC
    - Stagger chance scales (10/15/15/20%)
    - Stagger applies STAGGERED named effect (-2 hit, 1 round)
    - Anti-stacking: already-staggered targets skipped
    - Boundary tests for d100 roll
    - weapon_type_key is set correctly

evennia test --settings settings tests.typeclass_tests.test_club
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_club(location=None):
    """Create a ClubNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.club_nft_item.ClubNFTItem",
        key="Test Club",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's club mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"club": level_int}


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

class TestClubMasteryOverrides(EvenniaTest):
    """Test club mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        club = _make_club()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(club.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks_low_mastery(self):
        club = _make_club()
        for level in range(4):  # UNSKILLED through EXPERT
            _set_mastery(self.char1, level)
            self.assertEqual(club.get_extra_attacks(self.char1), 0)

    def test_extra_attack_master(self):
        club = _make_club()
        _set_mastery(self.char1, 4)  # MASTER
        self.assertEqual(club.get_extra_attacks(self.char1), 1)

    def test_extra_attack_gm(self):
        club = _make_club()
        _set_mastery(self.char1, 5)  # GM
        self.assertEqual(club.get_extra_attacks(self.char1), 1)

    def test_weapon_type_key(self):
        club = _make_club()
        self.assertEqual(club.weapon_type_key, "club")

    def test_has_club_tag(self):
        club = _make_club()
        self.assertTrue(club.tags.has("club", category="weapon_type"))


# ================================================================== #
#  Stagger Tests
# ================================================================== #

class TestClubStagger(EvenniaTest):
    """Test light stagger mechanic on club."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.club = _make_club()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_no_stagger_unskilled(self, mock_dice):
        """UNSKILLED should never attempt stagger."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()
        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_no_stagger_basic(self, mock_dice):
        """BASIC should never attempt stagger."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_skilled_hit(self, mock_dice):
        """SKILLED: d100=8 <= 10% → stagger applied."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 8

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()
        args, kwargs = target.apply_staggered.call_args
        self.assertEqual(args[0], -2)  # hit_penalty
        self.assertEqual(args[1], 1)   # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_skilled_miss(self, mock_dice):
        """SKILLED: d100=15 > 10% → no stagger."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 15

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_expert(self, mock_dice):
        """EXPERT: d100=12 <= 15% → stagger."""
        _set_mastery(self.char1, 3)
        target = _mock_target()
        mock_dice.roll.return_value = 12

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_master(self, mock_dice):
        """MASTER: d100=13 <= 15% → stagger."""
        _set_mastery(self.char1, 4)
        target = _mock_target()
        mock_dice.roll.return_value = 13

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_gm(self, mock_dice):
        """GM: d100=18 <= 20% → stagger."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 18

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_boundary_passes(self, mock_dice):
        """d100 exactly equal to chance should pass."""
        _set_mastery(self.char1, 2)  # SKILLED: 10%
        target = _mock_target()
        mock_dice.roll.return_value = 10

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_called_once()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_boundary_fails(self, mock_dice):
        """d100 one above chance should fail."""
        _set_mastery(self.char1, 2)  # SKILLED: 10%
        target = _mock_target()
        mock_dice.roll.return_value = 11

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_skip_already_staggered(self, mock_dice):
        """Already-staggered targets should not be staggered again."""
        _set_mastery(self.char1, 5)
        target = _mock_target(already_staggered=True)
        mock_dice.roll.return_value = 1

        self.club.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_staggered.assert_not_called()

    @patch("typeclasses.items.weapons.club_nft_item.dice")
    def test_stagger_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 1

        result = self.club.at_hit(self.char1, target, 42, "bludgeoning")

        self.assertEqual(result, 42)

"""
Tests for SlingNFTItem — sling with concussive daze mastery.

Validates:
    - No parries, extra attacks at EXPERT+ (0/0/0/1/1/1)
    - No daze at UNSKILLED/BASIC
    - Daze chance scales (10/15/20/25%)
    - Daze applies STUNNED named effect (1 round)
    - Size gate: HUGE+ immune
    - Anti-stacking: already-stunned targets skipped
    - Boundary tests for d100 roll
    - weapon_type_key is set correctly

evennia test --settings settings tests.typeclass_tests.test_sling
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from enums.size import Size


def _make_sling(location=None):
    """Create a SlingNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.sling_nft_item.SlingNFTItem",
        key="Test Sling",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's sling mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"sling": level_int}


def _mock_target(already_stunned=False, size="medium"):
    """Create a mock target for daze testing."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.has_effect.return_value = already_stunned
    target.apply_stunned = MagicMock(return_value=True)
    # get_actor_size checks actor.race.size first — set race=None so it
    # falls through to actor.size (the mob path)
    target.race = None
    target.size = size
    return target


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestSlingMasteryOverrides(EvenniaTest):
    """Test sling mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        sling = _make_sling()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(sling.get_parries_per_round(self.char1), 0)

    def test_extra_attacks(self):
        """Sling gets extra attacks at EXPERT+: 0/0/0/1/1/1."""
        sling = _make_sling()
        expected = [0, 0, 0, 1, 1, 1]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sling.get_extra_attacks(self.char1), exp,
                             f"Level {level}: expected {exp}")

    def test_weapon_type_key(self):
        sling = _make_sling()
        self.assertEqual(sling.weapon_type_key, "sling")

    def test_has_sling_tag(self):
        sling = _make_sling()
        self.assertTrue(sling.tags.has("sling", category="weapon_type"))


# ================================================================== #
#  Daze Tests
# ================================================================== #

class TestSlingDaze(EvenniaTest):
    """Test concussive daze mechanic on sling."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.sling = _make_sling()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_no_daze_unskilled(self, mock_dice):
        """UNSKILLED should never attempt daze."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()
        target.apply_stunned.assert_not_called()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_no_daze_basic(self, mock_dice):
        """BASIC should never attempt daze."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_skilled_hit(self, mock_dice):
        """SKILLED: d100=8 <= 10% → daze applied."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 8

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()
        args, kwargs = target.apply_stunned.call_args
        self.assertEqual(args[0], 1)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_skilled_miss(self, mock_dice):
        """SKILLED: d100=15 > 10% → no daze."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 15

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_not_called()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_expert(self, mock_dice):
        """EXPERT: d100=12 <= 15% → daze."""
        _set_mastery(self.char1, 3)
        target = _mock_target()
        mock_dice.roll.return_value = 12

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_master(self, mock_dice):
        """MASTER: d100=18 <= 20% → daze."""
        _set_mastery(self.char1, 4)
        target = _mock_target()
        mock_dice.roll.return_value = 18

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_gm(self, mock_dice):
        """GM: d100=22 <= 25% → daze."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 22

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_boundary_passes(self, mock_dice):
        """d100 exactly equal to chance should pass."""
        _set_mastery(self.char1, 2)  # SKILLED: 10%
        target = _mock_target()
        mock_dice.roll.return_value = 10

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_boundary_fails(self, mock_dice):
        """d100 one above chance should fail."""
        _set_mastery(self.char1, 2)  # SKILLED: 10%
        target = _mock_target()
        mock_dice.roll.return_value = 11

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_not_called()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_immune_huge(self, mock_dice):
        """HUGE targets should be immune to daze."""
        _set_mastery(self.char1, 5)
        target = _mock_target(size="huge")
        mock_dice.roll.return_value = 1

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_not_called()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_immune_gargantuan(self, mock_dice):
        """GARGANTUAN targets should be immune to daze."""
        _set_mastery(self.char1, 5)
        target = _mock_target(size="gargantuan")
        mock_dice.roll.return_value = 1

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_not_called()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_skip_already_stunned(self, mock_dice):
        """Already-stunned targets should not be dazed again."""
        _set_mastery(self.char1, 5)
        target = _mock_target(already_stunned=True)
        mock_dice.roll.return_value = 1

        self.sling.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_not_called()

    @patch("typeclasses.items.weapons.sling_nft_item.dice")
    def test_daze_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 1

        result = self.sling.at_hit(self.char1, target, 42, "bludgeoning")

        self.assertEqual(result, 42)

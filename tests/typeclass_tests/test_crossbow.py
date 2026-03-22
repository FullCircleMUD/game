"""
Tests for CrossbowNFTItem — crossbow with knockback mastery.

Validates:
    - No parries, no extra attacks
    - No knockback at UNSKILLED/BASIC
    - Knockback chance scales (15/20/25/30%)
    - Knockback applies PRONE named effect
    - Size gate: HUGE+ immune
    - Anti-stacking: already-prone targets skipped
    - Boundary tests for d100 roll

evennia test --settings settings tests.typeclass_tests.test_crossbow
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_crossbow(location=None):
    """Create a CrossbowNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.crossbow_nft_item.CrossbowNFTItem",
        key="Test Crossbow",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's crossbow mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"crossbow": level_int}


def _mock_target(already_prone=False, size="medium"):
    """Create a mock target for knockback testing."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.has_effect.return_value = already_prone
    target.apply_prone = MagicMock(return_value=True)
    # get_actor_size checks actor.race.size first — set race=None so it
    # falls through to actor.size (the mob path)
    target.race = None
    target.size = size
    return target


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestCrossbowMasteryOverrides(EvenniaTest):
    """Test crossbow mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        xbow = _make_crossbow()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(xbow.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks(self):
        xbow = _make_crossbow()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(xbow.get_extra_attacks(self.char1), 0)

    def test_weapon_type_key(self):
        xbow = _make_crossbow()
        self.assertEqual(xbow.weapon_type_key, "crossbow")

    def test_has_crossbow_tag(self):
        xbow = _make_crossbow()
        self.assertTrue(xbow.tags.has("crossbow", category="weapon_type"))


# ================================================================== #
#  Knockback Tests
# ================================================================== #

class TestCrossbowKnockback(EvenniaTest):
    """Test knockback/prone mechanic on crossbow."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.xbow = _make_crossbow()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_no_knockback_unskilled(self, mock_dice):
        """UNSKILLED should never attempt knockback."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_no_knockback_basic(self, mock_dice):
        """BASIC should never attempt knockback."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_skilled_hit(self, mock_dice):
        """SKILLED: d100=12 <= 15% → knockback applied."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 12

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_called_once()
        args, kwargs = target.apply_prone.call_args
        self.assertEqual(args[0], 1)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_skilled_miss(self, mock_dice):
        """SKILLED: d100=20 > 15% → no knockback."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 20

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_expert(self, mock_dice):
        """EXPERT: d100=18 <= 20% → knockback."""
        _set_mastery(self.char1, 3)
        target = _mock_target()
        mock_dice.roll.return_value = 18

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_called_once()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_master(self, mock_dice):
        """MASTER: d100=22 <= 25% → knockback."""
        _set_mastery(self.char1, 4)
        target = _mock_target()
        mock_dice.roll.return_value = 22

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_called_once()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_gm(self, mock_dice):
        """GM: d100=28 <= 30% → knockback."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 28

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_called_once()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_boundary_passes(self, mock_dice):
        """d100 exactly equal to chance should pass."""
        _set_mastery(self.char1, 2)  # SKILLED: 15%
        target = _mock_target()
        mock_dice.roll.return_value = 15

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_called_once()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_boundary_fails(self, mock_dice):
        """d100 one above chance should fail."""
        _set_mastery(self.char1, 2)  # SKILLED: 15%
        target = _mock_target()
        mock_dice.roll.return_value = 16

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_immune_huge(self, mock_dice):
        """HUGE targets should be immune to knockback."""
        _set_mastery(self.char1, 5)  # GM: 30%
        target = _mock_target(size="huge")
        mock_dice.roll.return_value = 1  # guaranteed pass if not immune

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_immune_gargantuan(self, mock_dice):
        """GARGANTUAN targets should be immune to knockback."""
        _set_mastery(self.char1, 5)
        target = _mock_target(size="gargantuan")
        mock_dice.roll.return_value = 1

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_skip_already_prone(self, mock_dice):
        """Already-prone targets should not be knocked prone again."""
        _set_mastery(self.char1, 5)
        target = _mock_target(already_prone=True)
        mock_dice.roll.return_value = 1

        self.xbow.at_hit(self.char1, target, 5, "piercing")

        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.crossbow_nft_item.dice")
    def test_knockback_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 1

        result = self.xbow.at_hit(self.char1, target, 42, "piercing")

        self.assertEqual(result, 42)

"""
Tests for AxeNFTItem — handaxe with sunder + extra attack mastery.

Validates:
    - No parries, extra attacks at MASTER/GM
    - Sunder does nothing at UNSKILLED/BASIC
    - Sunder triggers with reduced chances (10/15/15/20%)
    - Sunder always -1 AC per proc (lighter than battleaxe)
    - Sunder stacks, AC floor of 10
    - Sunder extra durability damage to body armour
    - Extra attack at MASTER (1) and GM (1)

evennia test --settings settings tests.typeclass_tests.test_axe
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_axe(location=None):
    """Create an AxeNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.axe_nft_item.AxeNFTItem",
        key="Test Axe",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's handaxe mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"handaxe": level_int}


def _mock_target(armor_class=15, has_sundered=False, sunder_stacks=0):
    """Create a mock target for sunder testing."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.armor_class = armor_class
    target.has_effect.return_value = has_sundered
    target.apply_sundered = MagicMock(return_value=True)
    target.db.sunder_stacks = sunder_stacks if has_sundered else 0
    target.get_slot.return_value = None
    return target


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestAxeMasteryOverrides(EvenniaTest):
    """Test handaxe mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        axe = _make_axe()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(axe.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks_before_master(self):
        axe = _make_axe()
        for level in range(4):  # UNSKILLED through EXPERT
            _set_mastery(self.char1, level)
            self.assertEqual(axe.get_extra_attacks(self.char1), 0)

    def test_extra_attack_at_master(self):
        axe = _make_axe()
        _set_mastery(self.char1, 4)  # MASTER
        self.assertEqual(axe.get_extra_attacks(self.char1), 1)

    def test_extra_attack_at_gm(self):
        axe = _make_axe()
        _set_mastery(self.char1, 5)  # GM
        self.assertEqual(axe.get_extra_attacks(self.char1), 1)

    def test_weapon_type_key(self):
        axe = _make_axe()
        self.assertEqual(axe.weapon_type_key, "handaxe")

    def test_has_axe_tag(self):
        axe = _make_axe()
        self.assertTrue(axe.tags.has("axe", category="weapon_type"))


# ================================================================== #
#  Sunder Tests
# ================================================================== #

class TestAxeSunder(EvenniaTest):
    """Test stacking sunder mechanic on handaxe."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.axe = _make_axe()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_no_sunder_unskilled(self, mock_dice):
        """UNSKILLED should never attempt sunder."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.axe.at_hit(self.char1, target, 5, "slashing")

        mock_dice.roll.assert_not_called()
        target.apply_sundered.assert_not_called()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_no_sunder_basic(self, mock_dice):
        """BASIC should never attempt sunder."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.axe.at_hit(self.char1, target, 5, "slashing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_skilled_hit(self, mock_dice):
        """SKILLED: d100=8 <= 10% → sunder applied with -1 AC."""
        _set_mastery(self.char1, 2)
        target = _mock_target(armor_class=15)
        mock_dice.roll.return_value = 8

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_called_once()
        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -1)  # ac_penalty
        self.assertEqual(args[1], 99)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_skilled_miss(self, mock_dice):
        """SKILLED: d100=15 > 10% → no sunder."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        mock_dice.roll.return_value = 15

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_not_called()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_expert_hit(self, mock_dice):
        """EXPERT: d100=12 <= 15% → sunder applied with -1 AC."""
        _set_mastery(self.char1, 3)
        target = _mock_target(armor_class=15)
        mock_dice.roll.return_value = 12

        self.axe.at_hit(self.char1, target, 5, "slashing")

        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -1)  # ac_penalty

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_always_minus_one(self, mock_dice):
        """Handaxe sunder is always -1 AC per proc, even at GM."""
        _set_mastery(self.char1, 5)  # GM
        target = _mock_target(armor_class=20)
        mock_dice.roll.return_value = 15

        self.axe.at_hit(self.char1, target, 5, "slashing")

        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -1)  # ac_penalty

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_stacks(self, mock_dice):
        """Second sunder on same target should stack to -2 AC."""
        _set_mastery(self.char1, 2)
        target = _mock_target(armor_class=14, has_sundered=True, sunder_stacks=1)
        mock_dice.roll.return_value = 8

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.remove_named_effect.assert_called_once_with("sundered")
        target.apply_sundered.assert_called_once()
        args, kwargs = target.apply_sundered.call_args
        self.assertEqual(args[0], -2)  # ac_penalty (stacked)

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_ac_floor(self, mock_dice):
        """Sunder should not reduce armor_class below 10."""
        _set_mastery(self.char1, 2)
        target = _mock_target(armor_class=10, has_sundered=False)
        mock_dice.roll.return_value = 8

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_not_called()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_ac_floor_with_stacks(self, mock_dice):
        """Sunder should stop stacking when AC hits floor."""
        _set_mastery(self.char1, 2)
        # base AC was 12, currently 10 with 2 stacks
        target = _mock_target(armor_class=10, has_sundered=True, sunder_stacks=2)
        mock_dice.roll.return_value = 8

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_not_called()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_extra_durability(self, mock_dice):
        """Sunder should deal +1 extra durability to body armour."""
        _set_mastery(self.char1, 2)
        body_armor = MagicMock()
        body_armor.reduce_durability = MagicMock()
        target = _mock_target(armor_class=15)
        target.get_slot.return_value = body_armor
        mock_dice.roll.return_value = 8

        self.axe.at_hit(self.char1, target, 5, "slashing")

        body_armor.reduce_durability.assert_called_once_with(1)

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_no_body_armor(self, mock_dice):
        """Sunder on target without body armour should not error."""
        _set_mastery(self.char1, 2)
        target = _mock_target(armor_class=15)
        target.get_slot.return_value = None
        mock_dice.roll.return_value = 8

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_called_once()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged regardless of sunder."""
        _set_mastery(self.char1, 5)
        target = _mock_target()
        mock_dice.roll.return_value = 1

        result = self.axe.at_hit(self.char1, target, 42, "slashing")

        self.assertEqual(result, 42)

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_stores_stacks(self, mock_dice):
        """Sunder should store cumulative stacks on target.db.sunder_stacks."""
        _set_mastery(self.char1, 2)
        target = _mock_target(armor_class=15)
        mock_dice.roll.return_value = 8

        self.axe.at_hit(self.char1, target, 5, "slashing")

        self.assertEqual(target.db.sunder_stacks, 1)

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_boundary_passes(self, mock_dice):
        """d100 roll exactly equal to chance should pass."""
        _set_mastery(self.char1, 2)  # SKILLED: 10%
        target = _mock_target(armor_class=15)
        mock_dice.roll.return_value = 10

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_called_once()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_sunder_boundary_fails(self, mock_dice):
        """d100 roll one above chance should fail."""
        _set_mastery(self.char1, 2)  # SKILLED: 10%
        target = _mock_target(armor_class=15)
        mock_dice.roll.return_value = 11

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_not_called()

    @patch("typeclasses.items.weapons.axe_nft_item.dice")
    def test_gm_sunder_chance(self, mock_dice):
        """GM: 20% sunder chance — d100=18 should pass."""
        _set_mastery(self.char1, 5)
        target = _mock_target(armor_class=15)
        mock_dice.roll.return_value = 18

        self.axe.at_hit(self.char1, target, 5, "slashing")

        target.apply_sundered.assert_called_once()

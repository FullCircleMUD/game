"""
Tests for SaiNFTItem — disarm + parry specialist.

Validates:
    - Parries: 0/0/1/2/2/3
    - Parry advantage: F/F/F/F/T/T
    - Riposte: only at GM
    - No extra attacks at any level
    - Off-hand attacks: 0/0/1/1/1/2
    - Off-hand penalty: 0/0/-4/-2/0/0
    - Disarm checks per round: 0/0/1/1/1/2
    - Disarm mechanic (contested DEX vs STR):
        - No disarm at UNSKILLED/BASIC
        - Win → target's weapon unequipped to inventory
        - Size gate: HUGE+ immune
        - Anti-stacking: unarmed targets skipped

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
        expected = [0, 0, 1, 2, 2, 3]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_parries_per_round(self.char1), exp,
                             f"Level {level}: expected {exp}")

    def test_parry_advantage(self):
        sai = _make_sai()
        expected = [False, False, False, False, True, True]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_parry_advantage(self.char1), exp,
                             f"Level {level}: expected {exp}")

    def test_riposte(self):
        sai = _make_sai()
        for level in range(5):
            _set_mastery(self.char1, level)
            self.assertFalse(sai.has_riposte(self.char1),
                             f"Level {level} should NOT have riposte")
        _set_mastery(self.char1, 5)
        self.assertTrue(sai.has_riposte(self.char1), "GM should have riposte")

    def test_offhand_attacks(self):
        sai = _make_sai()
        expected = [0, 0, 1, 1, 1, 2]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_offhand_attacks(self.char1), exp,
                             f"Level {level}: expected {exp}")

    def test_offhand_penalty(self):
        sai = _make_sai()
        expected = [0, 0, -4, -2, 0, 0]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_offhand_hit_modifier(self.char1), exp,
                             f"Level {level}: expected {exp}")

    def test_disarm_checks_per_round(self):
        sai = _make_sai()
        expected = [0, 0, 1, 1, 1, 2]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_disarm_checks_per_round(self.char1), exp,
                             f"Level {level}: expected {exp}")


# ================================================================== #
#  Disarm Mechanic Tests
# ================================================================== #

class TestSaiDisarm(EvenniaTest):
    """Test contested DEX vs STR disarm mechanic."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.sai = _make_sai()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_no_disarm_unskilled(self, mock_dice, mock_get_weapon):
        """UNSKILLED should never attempt disarm."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.sai.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()
        target.remove.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_no_disarm_basic(self, mock_dice, mock_get_weapon):
        """BASIC should never attempt disarm."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.sai.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_disarm_skilled_success(self, mock_dice, mock_get_weapon):
        """SKILLED: attacker wins contested roll → weapon unequipped."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = lambda x: 3 if x == 16 else 0

        target_weapon = _mock_target_weapon()
        mock_get_weapon.return_value = target_weapon
        target = _mock_target(weapon=target_weapon)

        handler = _mock_handler(disarm_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker: 15 + 3 DEX + 2 mastery = 20
        # Defender: 10 + 0 STR + 0 target mastery = 10
        mock_dice.roll.side_effect = [15, 10]

        self.sai.at_hit(self.char1, target, 5, "piercing")

        target.remove.assert_called_once_with(target_weapon)
        self.assertEqual(handler.disarm_checks_remaining, 0)

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_disarm_skilled_failure(self, mock_dice, mock_get_weapon):
        """SKILLED: defender wins → no disarm."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0

        target_weapon = _mock_target_weapon()
        mock_get_weapon.return_value = target_weapon
        target = _mock_target(weapon=target_weapon)

        handler = _mock_handler(disarm_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker: 5 + 0 + 2 = 7, Defender: 15 + 0 + 0 = 15
        mock_dice.roll.side_effect = [5, 15]

        self.sai.at_hit(self.char1, target, 5, "piercing")

        target.remove.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_disarm_tie_no_effect(self, mock_dice, mock_get_weapon):
        """Tie (attacker == defender) → no disarm (must win strictly)."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0

        target_weapon = _mock_target_weapon()
        mock_get_weapon.return_value = target_weapon
        target = _mock_target(weapon=target_weapon)

        handler = _mock_handler(disarm_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Both roll 10, attacker + 2 mastery = 12, defender = 12 → tie
        mock_dice.roll.side_effect = [10, 12]

        self.sai.at_hit(self.char1, target, 5, "piercing")

        target.remove.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_immune_huge(self, mock_dice, mock_get_weapon):
        """HUGE targets should be immune to disarm."""
        _set_mastery(self.char1, 5)
        target_weapon = _mock_target_weapon()
        mock_get_weapon.return_value = target_weapon
        target = _mock_target(size="huge", weapon=target_weapon)

        handler = _mock_handler(disarm_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.sai.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()
        target.remove.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_immune_gargantuan(self, mock_dice, mock_get_weapon):
        """GARGANTUAN targets should be immune to disarm."""
        _set_mastery(self.char1, 5)
        target_weapon = _mock_target_weapon()
        mock_get_weapon.return_value = target_weapon
        target = _mock_target(size="gargantuan", weapon=target_weapon)

        handler = _mock_handler(disarm_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.sai.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_skip_unarmed_target(self, mock_dice, mock_get_weapon):
        """Unarmed targets (UnarmedWeapon singleton) should be skipped."""
        from typeclasses.items.weapons.unarmed_weapon import UNARMED
        _set_mastery(self.char1, 5)
        mock_get_weapon.return_value = UNARMED
        target = _mock_target()

        handler = _mock_handler(disarm_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.sai.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()
        target.remove.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_skip_no_weapon(self, mock_dice, mock_get_weapon):
        """Target with no weapon should be skipped."""
        _set_mastery(self.char1, 5)
        mock_get_weapon.return_value = None
        target = _mock_target()

        handler = _mock_handler(disarm_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.sai.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_no_check_when_exhausted(self, mock_dice, mock_get_weapon):
        """No disarm when disarm_checks_remaining = 0."""
        _set_mastery(self.char1, 2)
        target_weapon = _mock_target_weapon()
        mock_get_weapon.return_value = target_weapon
        target = _mock_target(weapon=target_weapon)

        handler = _mock_handler(disarm_checks=0)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.sai.at_hit(self.char1, target, 5, "piercing")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_returns_damage_unchanged(self, mock_dice, mock_get_weapon):
        """at_hit should return damage unchanged."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        result = self.sai.at_hit(self.char1, target, 42, "piercing")

        self.assertEqual(result, 42)

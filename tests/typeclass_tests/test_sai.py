"""
Tests for SaiNFTItem — parry-to-disarm specialist.

Validates:
    - Parries: 0/1/2/3/4/5
    - Disarm checks: 0/0/1/1/1/2
    - No parry advantage
    - No riposte
    - No extra attacks at any level
    - Disarm-on-parry mechanic (contested DEX vs STR)

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


def _mock_attacker_weapon():
    """Create a mock weapon for the attacker (disarm target)."""
    weapon = MagicMock()
    weapon.weapon_type_key = "long_sword"
    weapon.key = "Iron Longsword"
    return weapon


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

    def test_disarm_checks(self):
        """Disarm checks: 0/0/1/1/1/2 across mastery levels."""
        sai = _make_sai()
        expected = [0, 0, 1, 1, 1, 2]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(sai.get_disarm_checks_per_round(self.char1), exp,
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


# ================================================================== #
#  Disarm-on-Parry Tests
# ================================================================== #

class TestSaiDisarm(EvenniaTest):
    """Test sai disarm-on-parry mechanic."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.sai = _make_sai()
        _set_mastery(self.char1, MasteryLevel.SKILLED.value)  # default SKILLED
        self.handler = _mock_handler(disarm_checks=1)
        self.char1.scripts.get = MagicMock(return_value=[self.handler])

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_no_disarm_unskilled(self, mock_dice, mock_get_weapon, mock_fdw):
        """UNSKILLED: no disarm attempt, no roll."""
        _set_mastery(self.char1, MasteryLevel.UNSKILLED.value)
        self.sai._try_disarm(self.char1, self.char2)
        mock_dice.roll.assert_not_called()
        mock_fdw.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_no_disarm_basic(self, mock_dice, mock_get_weapon, mock_fdw):
        """BASIC: no disarm attempt, no roll."""
        _set_mastery(self.char1, MasteryLevel.BASIC.value)
        self.sai._try_disarm(self.char1, self.char2)
        mock_dice.roll.assert_not_called()
        mock_fdw.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_disarm_success(self, mock_dice, mock_get_weapon, mock_fdw):
        """SKILLED: wins contested roll, force_drop_weapon called."""
        mock_get_weapon.return_value = _mock_attacker_weapon()
        mock_dice.roll.side_effect = [15, 5]  # wielder 15, attacker 5
        mock_fdw.return_value = (True, "Iron Longsword")

        self.sai._try_disarm(self.char1, self.char2)

        mock_fdw.assert_called_once_with(self.char2)
        self.assertEqual(self.handler.disarm_checks_remaining, 0)

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_disarm_failure(self, mock_dice, mock_get_weapon, mock_fdw):
        """SKILLED: loses contested roll, weapon stays, check consumed."""
        mock_get_weapon.return_value = _mock_attacker_weapon()
        mock_dice.roll.side_effect = [5, 15]  # wielder 5, attacker 15

        self.sai._try_disarm(self.char1, self.char2)

        mock_fdw.assert_not_called()
        self.assertEqual(self.handler.disarm_checks_remaining, 0)

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_no_checks_remaining(self, mock_dice, mock_get_weapon, mock_fdw):
        """No disarm checks remaining — no roll."""
        self.handler.disarm_checks_remaining = 0
        mock_get_weapon.return_value = _mock_attacker_weapon()

        self.sai._try_disarm(self.char1, self.char2)

        mock_dice.roll.assert_not_called()
        mock_fdw.assert_not_called()

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_actor_size")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_gargantuan_immune(self, mock_dice, mock_gas, mock_get_weapon, mock_fdw):
        """GARGANTUAN target is immune to disarm."""
        from enums.size import Size
        mock_gas.return_value = Size.GARGANTUAN

        self.sai._try_disarm(self.char1, self.char2)

        mock_dice.roll.assert_not_called()
        mock_fdw.assert_not_called()
        # Check did NOT consume — size gate fires before check consumption
        self.assertEqual(self.handler.disarm_checks_remaining, 1)

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_unarmed_target_skipped(self, mock_dice, mock_get_weapon, mock_fdw):
        """Unarmed target — early return, no check consumed."""
        from typeclasses.items.weapons.unarmed_weapon import UnarmedWeapon
        mock_unarmed = MagicMock(spec=UnarmedWeapon)
        mock_unarmed.weapon_type_key = "unarmed"
        mock_get_weapon.return_value = mock_unarmed

        self.sai._try_disarm(self.char1, self.char2)

        mock_dice.roll.assert_not_called()
        mock_fdw.assert_not_called()
        # Check did NOT consume — unarmed gate fires before check consumption
        self.assertEqual(self.handler.disarm_checks_remaining, 1)

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_gm_two_checks(self, mock_dice, mock_get_weapon, mock_fdw):
        """GM: two disarm attempts per round."""
        _set_mastery(self.char1, MasteryLevel.GRANDMASTER.value)
        self.handler.disarm_checks_remaining = 2
        mock_get_weapon.return_value = _mock_attacker_weapon()

        # First attempt: success
        mock_dice.roll.side_effect = [15, 5]
        mock_fdw.return_value = (True, "Iron Longsword")
        self.sai._try_disarm(self.char1, self.char2)
        self.assertEqual(self.handler.disarm_checks_remaining, 1)
        mock_fdw.assert_called_once()

        # Second attempt: target now unarmed (already disarmed)
        mock_fdw.reset_mock()
        mock_dice.roll.reset_mock()
        from typeclasses.items.weapons.unarmed_weapon import UnarmedWeapon
        mock_unarmed = MagicMock(spec=UnarmedWeapon)
        mock_unarmed.weapon_type_key = "unarmed"
        mock_get_weapon.return_value = mock_unarmed
        self.sai._try_disarm(self.char1, self.char2)
        # No roll, no disarm — target already unarmed
        mock_dice.roll.assert_not_called()
        mock_fdw.assert_not_called()
        # Check not consumed (unarmed gate)
        self.assertEqual(self.handler.disarm_checks_remaining, 1)

    @patch("typeclasses.items.weapons.sai_nft_item.force_drop_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.get_weapon")
    @patch("typeclasses.items.weapons.sai_nft_item.dice")
    def test_disarm_messages(self, mock_dice, mock_get_weapon, mock_fdw):
        """Successful disarm sends three-perspective messages."""
        mock_get_weapon.return_value = _mock_attacker_weapon()
        mock_dice.roll.side_effect = [15, 5]
        mock_fdw.return_value = (True, "Iron Longsword")

        with patch.object(self.char1, "msg") as mock_wielder_msg, \
             patch.object(self.char2, "msg") as mock_attacker_msg:
            self.sai._try_disarm(self.char1, self.char2)

            # Wielder (defender) gets success message
            mock_wielder_msg.assert_called()
            wielder_msg = mock_wielder_msg.call_args[0][0]
            self.assertIn("*DISARM*", wielder_msg)
            self.assertIn("Iron Longsword", wielder_msg)

            # Attacker (victim) gets disarm message
            mock_attacker_msg.assert_called()
            attacker_msg = mock_attacker_msg.call_args[0][0]
            self.assertIn("*DISARM*", attacker_msg)
            self.assertIn("Iron Longsword", attacker_msg)

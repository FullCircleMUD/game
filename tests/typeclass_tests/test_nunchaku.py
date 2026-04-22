"""
Tests for NunchakuNFTItem — two-handed stun specialist.

Validates:
    - No parries at any mastery level
    - can_dual_wield is False (two-handed)
    - Extra attacks: 0/0/1/1/2/2
    - No off-hand attacks (two-handed)
    - Stun checks per round: 0/0/1/1/1/2
    - Stun mechanic (contested DEX vs CON):
        - No stun at UNSKILLED/BASIC
        - SKILLED/EXPERT: win → STUNNED 1 round
        - MASTER: win by <5 → STUNNED 1, win by >=5 → PRONE 1
        - GM: STUNNED 2 / PRONE 2
        - Size gate: HUGE+ immune
        - Anti-stacking: stunned/prone targets skipped

evennia test --settings settings tests.typeclass_tests.test_nunchaku
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel
from enums.size import Size


def _make_nunchaku():
    """Create a NunchakuNFTItem for testing."""
    return create.create_object(
        "typeclasses.items.weapons.nunchaku_nft_item.NunchakuNFTItem",
        key="Test Nunchaku",
        nohome=True,
    )


def _set_mastery(char, level_int):
    """Set char's nunchaku mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"nanchaku": level_int}


def _mock_target(already_stunned=False, already_prone=False, size="medium"):
    """Create a mock target for stun testing."""
    target = MagicMock()
    target.key = "Target"
    target.hp = 100
    target.constitution = 10
    target.get_attribute_bonus.return_value = 0
    target.race = None
    target.size = size

    def _has_effect(key):
        if key == "stunned":
            return already_stunned
        if key == "prone":
            return already_prone
        return False
    target.has_effect.side_effect = _has_effect
    target.apply_stunned = MagicMock(return_value=True)
    target.apply_prone = MagicMock(return_value=True)
    return target


def _mock_handler(stun_checks=1):
    """Create a mock combat handler."""
    handler = MagicMock()
    handler.stun_checks_remaining = stun_checks
    return handler


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestNunchakuMasteryOverrides(EvenniaTest):
    """Test nunchaku mastery returns."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        nunchaku = _make_nunchaku()
        self.assertEqual(nunchaku.weapon_type_key, "nanchaku")

    def test_has_nanchaku_tag(self):
        nunchaku = _make_nunchaku()
        self.assertTrue(nunchaku.tags.has("nanchaku", category="weapon_type"))

    def test_can_dual_wield(self):
        nunchaku = _make_nunchaku()
        self.assertFalse(nunchaku.can_dual_wield)

    def test_no_parries(self):
        nunchaku = _make_nunchaku()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(nunchaku.get_parries_per_round(self.char1), 0)

    def test_extra_attacks(self):
        nunchaku = _make_nunchaku()
        expected = [0, 0, 1, 1, 2, 2]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(nunchaku.get_extra_attacks(self.char1), exp,
                             f"Level {level}: expected {exp}")

    def test_stun_checks_per_round(self):
        nunchaku = _make_nunchaku()
        expected = [0, 0, 1, 1, 1, 2]
        for level, exp in enumerate(expected):
            _set_mastery(self.char1, level)
            self.assertEqual(nunchaku.get_stun_checks_per_round(self.char1), exp,
                             f"Level {level}: expected {exp}")


# ================================================================== #
#  Stun Mechanic Tests
# ================================================================== #

class TestNunchakuStun(EvenniaTest):
    """Test contested DEX vs CON stun mechanic."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.nunchaku = _make_nunchaku()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_no_stun_unskilled(self, mock_dice):
        """UNSKILLED should never attempt stun."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()
        target.apply_stunned.assert_not_called()
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_no_stun_basic(self, mock_dice):
        """BASIC should never attempt stun."""
        _set_mastery(self.char1, 1)
        target = _mock_target()

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_stun_skilled_success(self, mock_dice):
        """SKILLED: attacker wins contested roll → STUNNED 1 round."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 16
        self.char1.get_attribute_bonus = lambda x: 3 if x == 16 else 0
        target = _mock_target()
        handler = _mock_handler(stun_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker rolls 15 + 3 DEX + 2 mastery = 20
        # Defender rolls 10 + 0 CON = 10
        mock_dice.roll.side_effect = [15, 10]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()
        args, kwargs = target.apply_stunned.call_args
        self.assertEqual(args[0], 1)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)
        self.assertEqual(handler.stun_checks_remaining, 0)

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_stun_skilled_failure(self, mock_dice):
        """SKILLED: defender wins contested roll → no stun."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target()
        handler = _mock_handler(stun_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker rolls 5 + 0 + 2 = 7, Defender rolls 15 + 0 = 15
        mock_dice.roll.side_effect = [5, 15]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_not_called()
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_stun_tie_no_effect(self, mock_dice):
        """Tie (attacker == defender) → no stun (must win strictly)."""
        _set_mastery(self.char1, 2)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target()
        handler = _mock_handler(stun_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Both roll 10, attacker + 2 mastery = 12, defender = 12 → tie
        mock_dice.roll.side_effect = [10, 12]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_not_called()
        target.apply_prone.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_master_stun_small_gap(self, mock_dice):
        """MASTER: win by <5 → STUNNED 1 round."""
        _set_mastery(self.char1, 4)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target()
        handler = _mock_handler(stun_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker: 15 + 0 + 6 = 21, Defender: 10 + 0 = 10, gap = 11... too large
        # Let's make gap < 5: Attacker: 10 + 0 + 6 = 16, Defender: 13 + 0 = 13, gap = 3
        mock_dice.roll.side_effect = [10, 13]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()
        args, kwargs = target.apply_stunned.call_args
        self.assertEqual(args[0], 1)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_master_prone_big_gap(self, mock_dice):
        """MASTER: win by >=5 → PRONE 1 round."""
        _set_mastery(self.char1, 4)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target()
        handler = _mock_handler(stun_checks=1)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker: 15 + 0 + 6 = 21, Defender: 10 + 0 = 10, gap = 11
        mock_dice.roll.side_effect = [15, 10]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_prone.assert_called_once()
        args, kwargs = target.apply_prone.call_args
        self.assertEqual(args[0], 1)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_gm_stun_2_rounds(self, mock_dice):
        """GM: win by <5 → STUNNED 2 rounds."""
        _set_mastery(self.char1, 5)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target()
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker: 10 + 0 + 8 = 18, Defender: 15 + 0 = 15, gap = 3
        mock_dice.roll.side_effect = [10, 15]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_stunned.assert_called_once()
        args, kwargs = target.apply_stunned.call_args
        self.assertEqual(args[0], 2)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_gm_prone_2_rounds(self, mock_dice):
        """GM: win by >=5 → PRONE 2 rounds."""
        _set_mastery(self.char1, 5)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target()
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        # Attacker: 18 + 0 + 8 = 26, Defender: 10 + 0 = 10, gap = 16
        mock_dice.roll.side_effect = [18, 10]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        target.apply_prone.assert_called_once()
        args, kwargs = target.apply_prone.call_args
        self.assertEqual(args[0], 2)  # duration_rounds
        self.assertEqual(kwargs["source"], self.char1)

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_immune_huge_target(self, mock_dice):
        """MEDIUM wielder vs HUGE target (2 sizes larger) — immune."""
        _set_mastery(self.char1, 5)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target(size="huge")
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        # Stun should be refused at the size gate
        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_immune_gargantuan_target(self, mock_dice):
        """MEDIUM wielder vs GARGANTUAN target (3 sizes larger) — immune."""
        _set_mastery(self.char1, 5)
        target = _mock_target(size="gargantuan")
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_not_immune_large_target(self, mock_dice):
        """MEDIUM wielder vs LARGE target (1 size larger) — not immune."""
        _set_mastery(self.char1, 5)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        target = _mock_target(size="large")
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        mock_dice.roll.side_effect = [15, 10]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        # Stun roll attempted
        mock_dice.roll.assert_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_large_wielder_vs_huge_target(self, mock_dice):
        """LARGE wielder can stun HUGE target — enlarge-spell synergy."""
        _set_mastery(self.char1, 5)
        self.char1.dexterity = 10
        self.char1.get_attribute_bonus = lambda x: 0
        self.char1.size = "large"
        target = _mock_target(size="huge")
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        mock_dice.roll.side_effect = [15, 10]

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_skip_already_stunned(self, mock_dice):
        """Already-stunned targets should be skipped."""
        _set_mastery(self.char1, 5)
        target = _mock_target(already_stunned=True)
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_skip_already_prone(self, mock_dice):
        """Already-prone targets should be skipped."""
        _set_mastery(self.char1, 5)
        target = _mock_target(already_prone=True)
        handler = _mock_handler(stun_checks=2)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_no_check_when_exhausted(self, mock_dice):
        """No stun when stun_checks_remaining = 0."""
        _set_mastery(self.char1, 2)
        target = _mock_target()
        handler = _mock_handler(stun_checks=0)
        self.char1.scripts.get = lambda key: [handler] if key == "combat_handler" else []

        self.nunchaku.at_hit(self.char1, target, 5, "bludgeoning")

        mock_dice.roll.assert_not_called()

    @patch("typeclasses.items.weapons.nunchaku_nft_item.dice")
    def test_returns_damage_unchanged(self, mock_dice):
        """at_hit should return damage unchanged."""
        _set_mastery(self.char1, 0)
        target = _mock_target()

        result = self.nunchaku.at_hit(self.char1, target, 42, "bludgeoning")

        self.assertEqual(result, 42)

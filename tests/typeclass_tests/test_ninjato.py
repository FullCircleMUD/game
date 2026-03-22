"""
Tests for NinjatoNFTItem — ninja signature sword with extra attacks, crit
reduction, and dual-wield off-hand attacks.

Validates:
    - Finesse flag set, can_dual_wield is True, ninja-only
    - No parries at any mastery level
    - Extra attacks: 0/0/0/+1/+1/+1
    - Off-hand attacks: 0/0/1/1/1/2
    - Off-hand penalty: 0/0/-4/-2/0/0
    - Crit modifier: 0/0/0/-1/-1/-2
    - Weapon type key and tag

evennia test --settings settings tests.typeclass_tests.test_ninjato
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_ninjato():
    """Create a NinjatoNFTItem for testing."""
    return create.create_object(
        "typeclasses.items.weapons.ninjato_nft_item.NinjatoNFTItem",
        key="Test Ninjato",
        nohome=True,
    )


def _set_mastery(char, level_int):
    """Set char's ninjato mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"ninjato": level_int}


class TestNinjatoMastery(EvenniaTest):
    """Test ninjato mastery overrides."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        ninjato = _make_ninjato()
        self.assertEqual(ninjato.weapon_type_key, "ninjato")

    def test_has_ninjato_tag(self):
        ninjato = _make_ninjato()
        self.assertTrue(ninjato.tags.has("ninjato", category="weapon_type"))

    def test_is_finesse(self):
        ninjato = _make_ninjato()
        self.assertTrue(ninjato.is_finesse)

    def test_can_dual_wield(self):
        ninjato = _make_ninjato()
        self.assertTrue(ninjato.can_dual_wield)

    def test_no_parries(self):
        """Ninjato should grant 0 parries at all mastery levels."""
        ninjato = _make_ninjato()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(ninjato.get_parries_per_round(self.char1), 0)

    # ── Extra Attacks ────────────────────────────────────────────────

    def test_extra_attacks_unskilled(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 0)
        self.assertEqual(ninjato.get_extra_attacks(self.char1), 0)

    def test_extra_attacks_basic(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 1)
        self.assertEqual(ninjato.get_extra_attacks(self.char1), 0)

    def test_extra_attacks_skilled(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 2)
        self.assertEqual(ninjato.get_extra_attacks(self.char1), 0)

    def test_extra_attacks_expert(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 3)
        self.assertEqual(ninjato.get_extra_attacks(self.char1), 1)

    def test_extra_attacks_master(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 4)
        self.assertEqual(ninjato.get_extra_attacks(self.char1), 1)

    def test_extra_attacks_gm(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 5)
        self.assertEqual(ninjato.get_extra_attacks(self.char1), 1)

    # ── Off-hand Attacks ─────────────────────────────────────────────

    def test_offhand_attacks_unskilled(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 0)
        self.assertEqual(ninjato.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_basic(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 1)
        self.assertEqual(ninjato.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_skilled(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 2)
        self.assertEqual(ninjato.get_offhand_attacks(self.char1), 1)

    def test_offhand_attacks_expert(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 3)
        self.assertEqual(ninjato.get_offhand_attacks(self.char1), 1)

    def test_offhand_attacks_master(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 4)
        self.assertEqual(ninjato.get_offhand_attacks(self.char1), 1)

    def test_offhand_attacks_gm(self):
        """GM ninjato gets 2 off-hand attacks — highest in the game."""
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 5)
        self.assertEqual(ninjato.get_offhand_attacks(self.char1), 2)

    # ── Off-hand Penalty ─────────────────────────────────────────────

    def test_offhand_penalty_skilled(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 2)
        self.assertEqual(ninjato.get_offhand_hit_modifier(self.char1), -4)

    def test_offhand_penalty_expert(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 3)
        self.assertEqual(ninjato.get_offhand_hit_modifier(self.char1), -2)

    def test_offhand_penalty_master(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 4)
        self.assertEqual(ninjato.get_offhand_hit_modifier(self.char1), 0)

    def test_offhand_penalty_gm(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 5)
        self.assertEqual(ninjato.get_offhand_hit_modifier(self.char1), 0)

    # ── Crit Threshold Modifier ──────────────────────────────────────

    def test_crit_modifier_unskilled(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 0)
        self.assertEqual(ninjato.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_modifier_basic(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 1)
        self.assertEqual(ninjato.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_modifier_skilled(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 2)
        self.assertEqual(ninjato.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_modifier_expert(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 3)
        self.assertEqual(ninjato.get_mastery_crit_threshold_modifier(self.char1), -1)

    def test_crit_modifier_master(self):
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 4)
        self.assertEqual(ninjato.get_mastery_crit_threshold_modifier(self.char1), -1)

    def test_crit_modifier_gm(self):
        """GM ninjato gets -2 crit threshold — crits on 18+."""
        ninjato = _make_ninjato()
        _set_mastery(self.char1, 5)
        self.assertEqual(ninjato.get_mastery_crit_threshold_modifier(self.char1), -2)

    # ── Default Bonuses ──────────────────────────────────────────────

    def test_default_hit_bonus(self):
        """Ninjato uses default MasteryLevel.bonus for hit — no override."""
        ninjato = _make_ninjato()
        for level in MasteryLevel:
            _set_mastery(self.char1, level.value)
            self.assertEqual(
                ninjato.get_mastery_hit_bonus(self.char1), level.bonus
            )

    def test_no_stun_checks(self):
        """Ninjato should return 0 stun checks at all mastery levels."""
        ninjato = _make_ninjato()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(ninjato.get_stun_checks_per_round(self.char1), 0)

    def test_no_disarm_checks(self):
        """Ninjato should return 0 disarm checks at all mastery levels."""
        ninjato = _make_ninjato()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(ninjato.get_disarm_checks_per_round(self.char1), 0)

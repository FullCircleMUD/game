"""
Tests for DaggerNFTItem — fast finesse weapon with extra attacks, crit reduction,
and off-hand dual-wield attacks at MASTER+.

Validates:
    - Finesse flag set, can_dual_wield is True
    - No parries at any mastery level
    - Extra attacks: 0/0/+1/+1/+1/+1
    - Off-hand attacks: 0/0/0/0/1/1
    - Crit modifier: 0/0/0/-1/-1/-2
    - Weapon type key and tag

evennia test --settings settings tests.typeclass_tests.test_dagger
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_dagger():
    """Create a DaggerNFTItem for testing."""
    return create.create_object(
        "typeclasses.items.weapons.dagger_nft_item.DaggerNFTItem",
        key="Test Dagger",
        nohome=True,
    )


def _set_mastery(char, level_int):
    """Set char's dagger mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"dagger": level_int}


class TestDaggerMastery(EvenniaTest):
    """Test dagger mastery overrides."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        dagger = _make_dagger()
        self.assertEqual(dagger.weapon_type_key, "dagger")

    def test_has_dagger_tag(self):
        dagger = _make_dagger()
        self.assertTrue(dagger.tags.has("dagger", category="weapon_type"))

    def test_is_finesse(self):
        dagger = _make_dagger()
        self.assertTrue(dagger.is_finesse)

    def test_can_dual_wield(self):
        dagger = _make_dagger()
        self.assertTrue(dagger.can_dual_wield)

    def test_no_parries(self):
        """Dagger should grant 0 parries at all mastery levels."""
        dagger = _make_dagger()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(dagger.get_parries_per_round(self.char1), 0)

    # ── Extra Attacks (main hand) ──────────────────────────────────

    def test_extra_attacks_unskilled(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 0)
        self.assertEqual(dagger.get_extra_attacks(self.char1), 0)

    def test_extra_attacks_basic(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 1)
        self.assertEqual(dagger.get_extra_attacks(self.char1), 0)

    def test_extra_attacks_skilled(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 2)
        self.assertEqual(dagger.get_extra_attacks(self.char1), 1)

    def test_extra_attacks_expert(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 3)
        self.assertEqual(dagger.get_extra_attacks(self.char1), 1)

    def test_extra_attacks_master(self):
        """MASTER dagger: 1 main extra + 1 off-hand (total 2 extra attacks)."""
        dagger = _make_dagger()
        _set_mastery(self.char1, 4)
        self.assertEqual(dagger.get_extra_attacks(self.char1), 1)

    def test_extra_attacks_gm(self):
        """GM dagger: 1 main extra + 1 off-hand (total 2 extra attacks)."""
        dagger = _make_dagger()
        _set_mastery(self.char1, 5)
        self.assertEqual(dagger.get_extra_attacks(self.char1), 1)

    # ── Off-hand Attacks ─────────────────────────────────────────

    def test_offhand_attacks_unskilled(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 0)
        self.assertEqual(dagger.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_basic(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 1)
        self.assertEqual(dagger.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_skilled(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 2)
        self.assertEqual(dagger.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_expert(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 3)
        self.assertEqual(dagger.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_master(self):
        """MASTER dagger gets 1 off-hand attack."""
        dagger = _make_dagger()
        _set_mastery(self.char1, 4)
        self.assertEqual(dagger.get_offhand_attacks(self.char1), 1)

    def test_offhand_attacks_gm(self):
        """GM dagger gets 1 off-hand attack."""
        dagger = _make_dagger()
        _set_mastery(self.char1, 5)
        self.assertEqual(dagger.get_offhand_attacks(self.char1), 1)

    # ── Crit Threshold Modifier ───────────────────────────────────

    def test_crit_modifier_unskilled(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 0)
        self.assertEqual(dagger.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_modifier_basic(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 1)
        self.assertEqual(dagger.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_modifier_skilled(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 2)
        self.assertEqual(dagger.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_modifier_expert(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 3)
        self.assertEqual(dagger.get_mastery_crit_threshold_modifier(self.char1), -1)

    def test_crit_modifier_master(self):
        dagger = _make_dagger()
        _set_mastery(self.char1, 4)
        self.assertEqual(dagger.get_mastery_crit_threshold_modifier(self.char1), -1)

    def test_crit_modifier_gm(self):
        """GM dagger gets -2 crit threshold — crits on 18+."""
        dagger = _make_dagger()
        _set_mastery(self.char1, 5)
        self.assertEqual(dagger.get_mastery_crit_threshold_modifier(self.char1), -2)

    # ── Default Bonuses ───────────────────────────────────────────

    def test_default_hit_bonus(self):
        """Dagger uses default MasteryLevel.bonus for hit — no override."""
        dagger = _make_dagger()
        for level in MasteryLevel:
            _set_mastery(self.char1, level.value)
            self.assertEqual(
                dagger.get_mastery_hit_bonus(self.char1), level.bonus
            )

    def test_default_damage_bonus(self):
        """Dagger uses default MasteryLevel.bonus for damage — no override."""
        dagger = _make_dagger()
        for level in MasteryLevel:
            _set_mastery(self.char1, level.value)
            self.assertEqual(
                dagger.get_mastery_damage_bonus(self.char1), level.bonus
            )

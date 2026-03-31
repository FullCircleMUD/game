"""
Tests for ShortswordNFTItem — dual-wield specialist with light parry.

Validates:
    - Weapon type key and tag
    - can_dual_wield is True
    - No extra main-hand attacks at any mastery level
    - Parries: 0/0/1/1/1/2
    - Off-hand attacks: 0/0/0/1/1/1
    - Off-hand hit modifier: 0/0/0/-4/-2/0
    - Default hit/damage bonuses (from MasteryLevel.bonus)

evennia test --settings settings tests.typeclass_tests.test_shortsword
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_shortsword():
    """Create a ShortswordNFTItem for testing."""
    return create.create_object(
        "typeclasses.items.weapons.shortsword_nft_item.ShortswordNFTItem",
        key="Test Shortsword",
        nohome=True,
    )


def _set_mastery(char, level_int):
    """Set char's shortsword mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"shortsword": level_int}


class TestShortswordMastery(EvenniaTest):
    """Test shortsword mastery overrides."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        ss = _make_shortsword()
        self.assertEqual(ss.weapon_type_key, "shortsword")

    def test_has_shortsword_tag(self):
        ss = _make_shortsword()
        self.assertTrue(ss.tags.has("shortsword", category="weapon_type"))

    def test_can_dual_wield(self):
        ss = _make_shortsword()
        self.assertTrue(ss.can_dual_wield)

    # ── No Main-Hand Extra Attacks ───────────────────────────────

    def test_no_extra_attacks(self):
        """Shortsword should grant 0 main-hand extra attacks at all levels."""
        ss = _make_shortsword()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(ss.get_extra_attacks(self.char1), 0)

    # ── Parries ──────────────────────────────────────────────────

    def test_parries_unskilled(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 0)
        self.assertEqual(ss.get_parries_per_round(self.char1), 0)

    def test_parries_basic(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 1)
        self.assertEqual(ss.get_parries_per_round(self.char1), 0)

    def test_parries_skilled(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 2)
        self.assertEqual(ss.get_parries_per_round(self.char1), 1)

    def test_parries_expert(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 3)
        self.assertEqual(ss.get_parries_per_round(self.char1), 1)

    def test_parries_master(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 4)
        self.assertEqual(ss.get_parries_per_round(self.char1), 1)

    def test_parries_gm(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 5)
        self.assertEqual(ss.get_parries_per_round(self.char1), 2)

    # ── Off-hand Attacks ─────────────────────────────────────────

    def test_offhand_attacks_unskilled(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 0)
        self.assertEqual(ss.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_basic(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 1)
        self.assertEqual(ss.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_skilled(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 2)
        self.assertEqual(ss.get_offhand_attacks(self.char1), 0)

    def test_offhand_attacks_expert(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 3)
        self.assertEqual(ss.get_offhand_attacks(self.char1), 1)

    def test_offhand_attacks_master(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 4)
        self.assertEqual(ss.get_offhand_attacks(self.char1), 1)

    def test_offhand_attacks_gm(self):
        """GM shortsword gets 1 off-hand attack."""
        ss = _make_shortsword()
        _set_mastery(self.char1, 5)
        self.assertEqual(ss.get_offhand_attacks(self.char1), 1)

    # ── Off-hand Hit Modifier ────────────────────────────────────

    def test_offhand_penalty_unskilled(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 0)
        self.assertEqual(ss.get_offhand_hit_modifier(self.char1), 0)

    def test_offhand_penalty_basic(self):
        ss = _make_shortsword()
        _set_mastery(self.char1, 1)
        self.assertEqual(ss.get_offhand_hit_modifier(self.char1), 0)

    def test_offhand_penalty_skilled(self):
        """SKILLED: no off-hand attacks, so modifier is 0."""
        ss = _make_shortsword()
        _set_mastery(self.char1, 2)
        self.assertEqual(ss.get_offhand_hit_modifier(self.char1), 0)

    def test_offhand_penalty_expert(self):
        """EXPERT: -4 off-hand penalty."""
        ss = _make_shortsword()
        _set_mastery(self.char1, 3)
        self.assertEqual(ss.get_offhand_hit_modifier(self.char1), -4)

    def test_offhand_penalty_master(self):
        """MASTER: -2 off-hand penalty."""
        ss = _make_shortsword()
        _set_mastery(self.char1, 4)
        self.assertEqual(ss.get_offhand_hit_modifier(self.char1), -2)

    def test_offhand_penalty_gm(self):
        """GM: no off-hand penalty."""
        ss = _make_shortsword()
        _set_mastery(self.char1, 5)
        self.assertEqual(ss.get_offhand_hit_modifier(self.char1), 0)

    # ── Default Bonuses ──────────────────────────────────────────

    def test_default_hit_bonus(self):
        """Shortsword uses default MasteryLevel.bonus for hit — no override."""
        ss = _make_shortsword()
        for level in MasteryLevel:
            _set_mastery(self.char1, level.value)
            self.assertEqual(
                ss.get_mastery_hit_bonus(self.char1), level.bonus
            )

    def test_default_damage_bonus(self):
        """Shortsword uses default MasteryLevel.bonus for damage — no override."""
        ss = _make_shortsword()
        for level in MasteryLevel:
            _set_mastery(self.char1, level.value)
            self.assertEqual(
                ss.get_mastery_damage_bonus(self.char1), level.bonus
            )

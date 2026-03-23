"""
Tests for LongswordNFTItem — longsword with parry-focused mastery path.

Validates:
    - weapon_type_key and tag set correctly
    - NOT finesse
    - NOT can_dual_wield
    - Custom hit bonuses: -2/0/+2/+4/+4/+5
    - Parries scale: 0/0/1/2/2/3
    - Extra attacks: 0/0/0/0/1/1 (MASTER and GM only)
    - Parry advantage at GRANDMASTER only
    - No riposte at any mastery

evennia test --settings settings tests.typeclass_tests.test_longsword
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_longsword(location=None):
    """Create a LongswordNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem",
        key="Test Longsword",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's long_sword mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"long_sword": level_int}


# ================================================================== #
#  Identity Tests
# ================================================================== #

class TestLongswordIdentity(EvenniaTest):
    """Test longsword type key and tags."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        sword = _make_longsword()
        self.assertEqual(sword.weapon_type_key, "long_sword")

    def test_has_long_sword_tag(self):
        sword = _make_longsword()
        self.assertTrue(sword.tags.has("long_sword", category="weapon_type"))

    def test_not_finesse(self):
        sword = _make_longsword()
        self.assertFalse(sword.is_finesse)

    def test_not_dual_wield(self):
        sword = _make_longsword()
        self.assertFalse(sword.can_dual_wield)


# ================================================================== #
#  Hit Bonus Tests
# ================================================================== #

class TestLongswordHitBonus(EvenniaTest):
    """Test custom hit bonuses: -2/0/+2/+4/+4/+5."""

    def create_script(self):
        pass

    def test_hit_bonus_unskilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 0)
        self.assertEqual(sword.get_mastery_hit_bonus(self.char1), -2)

    def test_hit_bonus_basic(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 1)
        self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 0)

    def test_hit_bonus_skilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 2)
        self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 2)

    def test_hit_bonus_expert(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 3)
        self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 4)

    def test_hit_bonus_master(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 4)
        self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 4)

    def test_hit_bonus_gm(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 5)
        self.assertEqual(sword.get_mastery_hit_bonus(self.char1), 5)


# ================================================================== #
#  Parry Tests
# ================================================================== #

class TestLongswordParries(EvenniaTest):
    """Test parry scaling: 0/0/1/2/2/3."""

    def create_script(self):
        pass

    def test_no_parries_unskilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 0)
        self.assertEqual(sword.get_parries_per_round(self.char1), 0)

    def test_no_parries_basic(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 1)
        self.assertEqual(sword.get_parries_per_round(self.char1), 0)

    def test_one_parry_skilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 2)
        self.assertEqual(sword.get_parries_per_round(self.char1), 1)

    def test_two_parries_expert(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 3)
        self.assertEqual(sword.get_parries_per_round(self.char1), 2)

    def test_two_parries_master(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 4)
        self.assertEqual(sword.get_parries_per_round(self.char1), 2)

    def test_three_parries_gm(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 5)
        self.assertEqual(sword.get_parries_per_round(self.char1), 3)


# ================================================================== #
#  Extra Attack Tests
# ================================================================== #

class TestLongswordExtraAttacks(EvenniaTest):
    """Test extra attacks: 0/0/0/0/1/1 (MASTER and GM only)."""

    def create_script(self):
        pass

    def test_no_extra_attacks_unskilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 0)
        self.assertEqual(sword.get_extra_attacks(self.char1), 0)

    def test_no_extra_attacks_basic(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 1)
        self.assertEqual(sword.get_extra_attacks(self.char1), 0)

    def test_no_extra_attacks_skilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 2)
        self.assertEqual(sword.get_extra_attacks(self.char1), 0)

    def test_no_extra_attacks_expert(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 3)
        self.assertEqual(sword.get_extra_attacks(self.char1), 0)

    def test_one_extra_attack_master(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 4)
        self.assertEqual(sword.get_extra_attacks(self.char1), 1)

    def test_one_extra_attack_gm(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 5)
        self.assertEqual(sword.get_extra_attacks(self.char1), 1)


# ================================================================== #
#  Parry Advantage Tests
# ================================================================== #

class TestLongswordParryAdvantage(EvenniaTest):
    """Test parry advantage — GRANDMASTER only."""

    def create_script(self):
        pass

    def test_no_advantage_unskilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 0)
        self.assertFalse(sword.get_parry_advantage(self.char1))

    def test_no_advantage_basic(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 1)
        self.assertFalse(sword.get_parry_advantage(self.char1))

    def test_no_advantage_skilled(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 2)
        self.assertFalse(sword.get_parry_advantage(self.char1))

    def test_no_advantage_expert(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 3)
        self.assertFalse(sword.get_parry_advantage(self.char1))

    def test_no_advantage_master(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 4)
        self.assertFalse(sword.get_parry_advantage(self.char1))

    def test_advantage_gm(self):
        sword = _make_longsword()
        _set_mastery(self.char1, 5)
        self.assertTrue(sword.get_parry_advantage(self.char1))


# ================================================================== #
#  Riposte Tests
# ================================================================== #

class TestLongswordRiposte(EvenniaTest):
    """Longsword has no riposte at any mastery tier."""

    def create_script(self):
        pass

    def test_no_riposte_at_any_level(self):
        sword = _make_longsword()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertFalse(sword.has_riposte(self.char1))

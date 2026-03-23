"""
Tests for RapierNFTItem — rapier with finesse + riposte mastery path.

Validates:
    - weapon_type_key and tag set correctly
    - is_finesse = True
    - NOT can_dual_wield
    - Custom hit bonuses: -2/0/+2/+3/+4/+5
    - Parries scale: 0/0/1/1/2/3
    - No extra attacks at any mastery
    - Riposte at EXPERT+ (level >= 3)
    - Parry advantage at GRANDMASTER only

evennia test --settings settings tests.typeclass_tests.test_rapier
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_rapier(location=None):
    """Create a RapierNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.rapier_nft_item.RapierNFTItem",
        key="Test Rapier",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's rapier mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"rapier": level_int}


# ================================================================== #
#  Identity Tests
# ================================================================== #

class TestRapierIdentity(EvenniaTest):
    """Test rapier type key, tags, and finesse flag."""

    def create_script(self):
        pass

    def test_weapon_type_key(self):
        rapier = _make_rapier()
        self.assertEqual(rapier.weapon_type_key, "rapier")

    def test_has_rapier_tag(self):
        rapier = _make_rapier()
        self.assertTrue(rapier.tags.has("rapier", category="weapon_type"))

    def test_is_finesse(self):
        rapier = _make_rapier()
        self.assertTrue(rapier.is_finesse)

    def test_not_dual_wield(self):
        rapier = _make_rapier()
        self.assertFalse(rapier.can_dual_wield)


# ================================================================== #
#  Hit Bonus Tests
# ================================================================== #

class TestRapierHitBonus(EvenniaTest):
    """Test custom hit bonuses: -2/0/+2/+3/+4/+5."""

    def create_script(self):
        pass

    def test_hit_bonus_unskilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 0)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), -2)

    def test_hit_bonus_basic(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 1)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 0)

    def test_hit_bonus_skilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 2)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 2)

    def test_hit_bonus_expert(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 3)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 3)

    def test_hit_bonus_master(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 4)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 4)

    def test_hit_bonus_gm(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 5)
        self.assertEqual(rapier.get_mastery_hit_bonus(self.char1), 5)


# ================================================================== #
#  Parry Tests
# ================================================================== #

class TestRapierParries(EvenniaTest):
    """Test parry scaling: 0/0/1/1/2/3."""

    def create_script(self):
        pass

    def test_no_parries_unskilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 0)
        self.assertEqual(rapier.get_parries_per_round(self.char1), 0)

    def test_no_parries_basic(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 1)
        self.assertEqual(rapier.get_parries_per_round(self.char1), 0)

    def test_one_parry_skilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 2)
        self.assertEqual(rapier.get_parries_per_round(self.char1), 1)

    def test_one_parry_expert(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 3)
        self.assertEqual(rapier.get_parries_per_round(self.char1), 1)

    def test_two_parries_master(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 4)
        self.assertEqual(rapier.get_parries_per_round(self.char1), 2)

    def test_three_parries_gm(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 5)
        self.assertEqual(rapier.get_parries_per_round(self.char1), 3)


# ================================================================== #
#  Extra Attack Tests
# ================================================================== #

class TestRapierExtraAttacks(EvenniaTest):
    """Rapier has no extra attacks at any mastery tier."""

    def create_script(self):
        pass

    def test_no_extra_attacks_at_any_level(self):
        rapier = _make_rapier()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(rapier.get_extra_attacks(self.char1), 0)


# ================================================================== #
#  Riposte Tests
# ================================================================== #

class TestRapierRiposte(EvenniaTest):
    """Test riposte — unlocks at EXPERT (level 3)."""

    def create_script(self):
        pass

    def test_no_riposte_unskilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 0)
        self.assertFalse(rapier.has_riposte(self.char1))

    def test_no_riposte_basic(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 1)
        self.assertFalse(rapier.has_riposte(self.char1))

    def test_no_riposte_skilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 2)
        self.assertFalse(rapier.has_riposte(self.char1))

    def test_riposte_expert(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 3)
        self.assertTrue(rapier.has_riposte(self.char1))

    def test_riposte_master(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 4)
        self.assertTrue(rapier.has_riposte(self.char1))

    def test_riposte_gm(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 5)
        self.assertTrue(rapier.has_riposte(self.char1))


# ================================================================== #
#  Parry Advantage Tests
# ================================================================== #

class TestRapierParryAdvantage(EvenniaTest):
    """Test parry advantage — GRANDMASTER only."""

    def create_script(self):
        pass

    def test_no_advantage_unskilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 0)
        self.assertFalse(rapier.get_parry_advantage(self.char1))

    def test_no_advantage_basic(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 1)
        self.assertFalse(rapier.get_parry_advantage(self.char1))

    def test_no_advantage_skilled(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 2)
        self.assertFalse(rapier.get_parry_advantage(self.char1))

    def test_no_advantage_expert(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 3)
        self.assertFalse(rapier.get_parry_advantage(self.char1))

    def test_no_advantage_master(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 4)
        self.assertFalse(rapier.get_parry_advantage(self.char1))

    def test_advantage_gm(self):
        rapier = _make_rapier()
        _set_mastery(self.char1, 5)
        self.assertTrue(rapier.get_parry_advantage(self.char1))

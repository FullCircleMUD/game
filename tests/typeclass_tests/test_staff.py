"""
Tests for StaffNFTItem — staff with parry specialist mastery.

Validates:
    - No extra attacks at any mastery
    - Parries scale: 0/0/2/2/3/4
    - Parry advantage at EXPERT+ (earlier than any other weapon)
    - Riposte at MASTER+ (later than rapier's EXPERT)
    - Custom hit bonuses: -2/0/+2/+3/+4/+5
    - Two-handed
    - weapon_type_key and tag set correctly

evennia test --settings settings tests.typeclass_tests.test_staff
"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_staff(location=None):
    """Create a StaffNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.staff_nft_item.StaffNFTItem",
        key="Test Staff",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's staff mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"staff": level_int}


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestStaffMasteryOverrides(EvenniaTest):
    """Test staff mastery returns."""

    def create_script(self):
        pass

    def test_no_extra_attacks(self):
        staff = _make_staff()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(staff.get_extra_attacks(self.char1), 0)

    def test_weapon_type_key(self):
        staff = _make_staff()
        self.assertEqual(staff.weapon_type_key, "staff")

    def test_has_staff_tag(self):
        staff = _make_staff()
        self.assertTrue(staff.tags.has("staff", category="weapon_type"))

    def test_two_handed(self):
        staff = _make_staff()
        self.assertTrue(staff.two_handed)


# ================================================================== #
#  Parry Tests
# ================================================================== #

class TestStaffParries(EvenniaTest):
    """Test staff parry scaling."""

    def create_script(self):
        pass

    def test_no_parries_unskilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 0)
        self.assertEqual(staff.get_parries_per_round(self.char1), 0)

    def test_no_parries_basic(self):
        staff = _make_staff()
        _set_mastery(self.char1, 1)
        self.assertEqual(staff.get_parries_per_round(self.char1), 0)

    def test_two_parries_skilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 2)
        self.assertEqual(staff.get_parries_per_round(self.char1), 2)

    def test_two_parries_expert(self):
        staff = _make_staff()
        _set_mastery(self.char1, 3)
        self.assertEqual(staff.get_parries_per_round(self.char1), 2)

    def test_three_parries_master(self):
        staff = _make_staff()
        _set_mastery(self.char1, 4)
        self.assertEqual(staff.get_parries_per_round(self.char1), 3)

    def test_four_parries_gm(self):
        staff = _make_staff()
        _set_mastery(self.char1, 5)
        self.assertEqual(staff.get_parries_per_round(self.char1), 4)


# ================================================================== #
#  Parry Advantage Tests
# ================================================================== #

class TestStaffParryAdvantage(EvenniaTest):
    """Test parry advantage — EXPERT+ (earlier than longsword/rapier GM)."""

    def create_script(self):
        pass

    def test_no_advantage_unskilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 0)
        self.assertFalse(staff.get_parry_advantage(self.char1))

    def test_no_advantage_basic(self):
        staff = _make_staff()
        _set_mastery(self.char1, 1)
        self.assertFalse(staff.get_parry_advantage(self.char1))

    def test_no_advantage_skilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 2)
        self.assertFalse(staff.get_parry_advantage(self.char1))

    def test_advantage_expert(self):
        staff = _make_staff()
        _set_mastery(self.char1, 3)
        self.assertTrue(staff.get_parry_advantage(self.char1))

    def test_advantage_master(self):
        staff = _make_staff()
        _set_mastery(self.char1, 4)
        self.assertTrue(staff.get_parry_advantage(self.char1))

    def test_advantage_gm(self):
        staff = _make_staff()
        _set_mastery(self.char1, 5)
        self.assertTrue(staff.get_parry_advantage(self.char1))


# ================================================================== #
#  Riposte Tests
# ================================================================== #

class TestStaffRiposte(EvenniaTest):
    """Test riposte — MASTER+ (later than rapier's EXPERT)."""

    def create_script(self):
        pass

    def test_no_riposte_unskilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 0)
        self.assertFalse(staff.has_riposte(self.char1))

    def test_no_riposte_basic(self):
        staff = _make_staff()
        _set_mastery(self.char1, 1)
        self.assertFalse(staff.has_riposte(self.char1))

    def test_no_riposte_skilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 2)
        self.assertFalse(staff.has_riposte(self.char1))

    def test_no_riposte_expert(self):
        staff = _make_staff()
        _set_mastery(self.char1, 3)
        self.assertFalse(staff.has_riposte(self.char1))

    def test_riposte_master(self):
        staff = _make_staff()
        _set_mastery(self.char1, 4)
        self.assertTrue(staff.has_riposte(self.char1))

    def test_riposte_gm(self):
        staff = _make_staff()
        _set_mastery(self.char1, 5)
        self.assertTrue(staff.has_riposte(self.char1))


# ================================================================== #
#  Hit Bonus Tests
# ================================================================== #

class TestStaffHitBonus(EvenniaTest):
    """Test custom hit bonuses: -2/0/+2/+3/+4/+5."""

    def create_script(self):
        pass

    def test_hit_bonus_unskilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 0)
        self.assertEqual(staff.get_mastery_hit_bonus(self.char1), -2)

    def test_hit_bonus_basic(self):
        staff = _make_staff()
        _set_mastery(self.char1, 1)
        self.assertEqual(staff.get_mastery_hit_bonus(self.char1), 0)

    def test_hit_bonus_skilled(self):
        staff = _make_staff()
        _set_mastery(self.char1, 2)
        self.assertEqual(staff.get_mastery_hit_bonus(self.char1), 2)

    def test_hit_bonus_expert(self):
        staff = _make_staff()
        _set_mastery(self.char1, 3)
        self.assertEqual(staff.get_mastery_hit_bonus(self.char1), 3)

    def test_hit_bonus_master(self):
        staff = _make_staff()
        _set_mastery(self.char1, 4)
        self.assertEqual(staff.get_mastery_hit_bonus(self.char1), 4)

    def test_hit_bonus_gm(self):
        staff = _make_staff()
        _set_mastery(self.char1, 5)
        self.assertEqual(staff.get_mastery_hit_bonus(self.char1), 5)

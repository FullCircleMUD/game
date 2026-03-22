"""
Tests for ShurikenNFTItem — shuriken with multi-throw + crit + consumable.

Validates:
    - No parries
    - Extra attacks scale: 0/0/0/1/1/2
    - Crit threshold modifier: 0/0/-1/-1/-2/-2
    - Unbreakable (reduce_durability is no-op)
    - Consumable: on hit, shuriken moves to target inventory
    - Consumable: on miss, shuriken moves to room floor
    - Auto-equip next shuriken from inventory after throw

evennia test --settings settings tests.typeclass_tests.test_shuriken
"""

from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.mastery_level import MasteryLevel


def _make_shuriken(location=None):
    """Create a ShurikenNFTItem for testing."""
    obj = create.create_object(
        "typeclasses.items.weapons.shuriken_nft_item.ShurikenNFTItem",
        key="Test Shuriken",
        nohome=True,
    )
    if location:
        obj.move_to(location, quiet=True)
    return obj


def _set_mastery(char, level_int):
    """Set char's shuriken mastery to the given integer level."""
    char.db.weapon_skill_mastery_levels = {"shuriken": level_int}


# ================================================================== #
#  Mastery Override Tests
# ================================================================== #

class TestShurikenMasteryOverrides(EvenniaTest):
    """Test shuriken mastery returns."""

    def create_script(self):
        pass

    def test_no_parries(self):
        shuriken = _make_shuriken()
        for level in range(6):
            _set_mastery(self.char1, level)
            self.assertEqual(shuriken.get_parries_per_round(self.char1), 0)

    def test_no_extra_attacks_before_expert(self):
        shuriken = _make_shuriken()
        for level in range(3):  # UNSKILLED through SKILLED
            _set_mastery(self.char1, level)
            self.assertEqual(shuriken.get_extra_attacks(self.char1), 0)

    def test_extra_attacks_expert(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 3)  # EXPERT
        self.assertEqual(shuriken.get_extra_attacks(self.char1), 1)

    def test_extra_attacks_master(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 4)  # MASTER
        self.assertEqual(shuriken.get_extra_attacks(self.char1), 1)

    def test_extra_attacks_gm(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 5)  # GM
        self.assertEqual(shuriken.get_extra_attacks(self.char1), 2)

    def test_crit_mod_unskilled(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 0)
        self.assertEqual(shuriken.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_mod_basic(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 1)
        self.assertEqual(shuriken.get_mastery_crit_threshold_modifier(self.char1), 0)

    def test_crit_mod_skilled(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 2)
        self.assertEqual(shuriken.get_mastery_crit_threshold_modifier(self.char1), -1)

    def test_crit_mod_expert(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 3)
        self.assertEqual(shuriken.get_mastery_crit_threshold_modifier(self.char1), -1)

    def test_crit_mod_master(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 4)
        self.assertEqual(shuriken.get_mastery_crit_threshold_modifier(self.char1), -2)

    def test_crit_mod_gm(self):
        shuriken = _make_shuriken()
        _set_mastery(self.char1, 5)
        self.assertEqual(shuriken.get_mastery_crit_threshold_modifier(self.char1), -2)

    def test_weapon_type_key(self):
        shuriken = _make_shuriken()
        self.assertEqual(shuriken.weapon_type_key, "shuriken")

    def test_has_shuriken_tag(self):
        shuriken = _make_shuriken()
        self.assertTrue(shuriken.tags.has("shuriken", category="weapon_type"))


# ================================================================== #
#  Unbreakable Tests
# ================================================================== #

class TestShurikenUnbreakable(EvenniaTest):
    """Test that shurikens don't lose durability."""

    def create_script(self):
        pass

    def test_reduce_durability_is_noop(self):
        shuriken = _make_shuriken()
        # Set initial durability
        shuriken.db.durability = 10
        shuriken.reduce_durability(1)
        # Should still be 10 — reduce_durability is overridden to no-op
        self.assertEqual(shuriken.db.durability, 10)

    def test_reduce_durability_multiple(self):
        shuriken = _make_shuriken()
        shuriken.db.durability = 10
        shuriken.reduce_durability(5)
        self.assertEqual(shuriken.db.durability, 10)


# ================================================================== #
#  Consumable Tests
# ================================================================== #

class TestShurikenConsumable(EvenniaTest):
    """Test consumable mechanic — shuriken moves on throw."""

    def create_script(self):
        pass

    def test_on_hit_moves_to_target(self):
        """On hit, shuriken should move to target's inventory."""
        shuriken = _make_shuriken()
        shuriken.move_to(self.char1, quiet=True)
        # Wield it
        self.char1.db.wearslots = {"WIELD": shuriken, "HOLD": None}
        target = self.char2

        shuriken.at_post_attack(self.char1, target, True, 5)

        # Shuriken should now be in target's inventory
        self.assertEqual(shuriken.location, target)
        # Wield slot should be cleared
        self.assertIsNone(self.char1.db.wearslots["WIELD"])

    def test_on_miss_moves_to_room(self):
        """On miss, shuriken should fall to room floor."""
        shuriken = _make_shuriken()
        shuriken.move_to(self.char1, quiet=True)
        self.char1.db.wearslots = {"WIELD": shuriken, "HOLD": None}

        shuriken.at_miss(self.char1, self.char2)

        # Shuriken should be on the room floor
        self.assertEqual(shuriken.location, self.char1.location)
        self.assertIsNone(self.char1.db.wearslots["WIELD"])

    def test_auto_equip_next_shuriken(self):
        """After consuming a shuriken, next one from inventory auto-equips."""
        shuriken1 = _make_shuriken()
        shuriken2 = _make_shuriken()
        shuriken1.move_to(self.char1, quiet=True)
        shuriken2.move_to(self.char1, quiet=True)
        self.char1.db.wearslots = {"WIELD": shuriken1, "HOLD": None}

        shuriken1.at_post_attack(self.char1, self.char2, True, 5)

        # shuriken1 moved to target, shuriken2 should be auto-equipped
        self.assertEqual(self.char1.db.wearslots["WIELD"], shuriken2)

    def test_no_auto_equip_when_none_left(self):
        """If no shurikens left, WIELD slot stays empty."""
        shuriken = _make_shuriken()
        shuriken.move_to(self.char1, quiet=True)
        self.char1.db.wearslots = {"WIELD": shuriken, "HOLD": None}

        shuriken.at_post_attack(self.char1, self.char2, True, 5)

        # No more shurikens — WIELD should be None
        self.assertIsNone(self.char1.db.wearslots["WIELD"])

    def test_on_miss_no_hit_flag(self):
        """at_post_attack with hit=False should not move the shuriken."""
        shuriken = _make_shuriken()
        shuriken.move_to(self.char1, quiet=True)
        self.char1.db.wearslots = {"WIELD": shuriken, "HOLD": None}

        shuriken.at_post_attack(self.char1, self.char2, False, 0)

        # Miss is handled by at_miss, not at_post_attack
        # at_post_attack with hit=False should be a no-op
        # (the shuriken stays — at_miss handles consumption)
        self.assertEqual(shuriken.location, self.char1)

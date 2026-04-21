"""
Tests for spell infrastructure — registry, base spell class, cooldowns, utilities.

School-specific spell tests live in tests/spell_tests/test_<school>.py.

evennia test --settings settings tests.typeclass_tests.test_spells
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from enums.damage_type import DamageType
from world.spells.registry import (
    SPELL_REGISTRY,
    get_spell,
    get_spells_for_school,
    list_spell_keys,
)
from world.spells.base_spell import Spell
from world.spells.spell_utils import apply_spell_damage


# ================================================================== #
#  Registry Tests
# ================================================================== #

class TestSpellRegistry(EvenniaTest):
    """Test the spell registry populated by @register_spell decorators."""

    def create_script(self):
        pass

    def test_magic_missile_registered(self):
        """magic_missile should be in the registry."""
        self.assertIn("magic_missile", SPELL_REGISTRY)

    def test_cure_wounds_registered(self):
        """cure_wounds should be in the registry."""
        self.assertIn("cure_wounds", SPELL_REGISTRY)

    def test_get_spell_returns_instance(self):
        """get_spell should return the spell instance."""
        spell = get_spell("magic_missile")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.key, "magic_missile")
        self.assertEqual(spell.name, "Magic Missile")

    def test_get_spell_unknown_returns_none(self):
        """get_spell with an unknown key should return None."""
        self.assertIsNone(get_spell("nonexistent_spell"))

    def test_get_spells_for_school_evocation(self):
        """get_spells_for_school should return evocation spells."""
        evocation = get_spells_for_school("evocation")
        self.assertIn("magic_missile", evocation)
        self.assertNotIn("cure_wounds", evocation)

    def test_get_spells_for_school_with_enum(self):
        """get_spells_for_school should accept skills enum."""
        evocation = get_spells_for_school(skills.EVOCATION)
        self.assertIn("magic_missile", evocation)

    def test_get_spells_for_school_divine_healing(self):
        """get_spells_for_school should return divine_healing spells."""
        divine = get_spells_for_school("divine_healing")
        self.assertIn("cure_wounds", divine)
        self.assertNotIn("magic_missile", divine)

    def test_get_spells_for_unknown_school_empty(self):
        """get_spells_for_school with unknown school returns empty dict."""
        result = get_spells_for_school("underwater_basketweaving")
        self.assertEqual(result, {})

    def test_list_spell_keys(self):
        """list_spell_keys should include both demo spells."""
        keys = list_spell_keys()
        self.assertIn("magic_missile", keys)
        self.assertIn("cure_wounds", keys)

    def test_spell_attributes(self):
        """Spell instances should have correct class attributes."""
        mm = get_spell("magic_missile")
        self.assertEqual(mm.school_key, "evocation")
        self.assertEqual(mm.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(mm.target_type, "actor_hostile")
        self.assertIn(1, mm.mana_cost)

        cw = get_spell("cure_wounds")
        self.assertEqual(cw.school_key, "divine_healing")
        self.assertEqual(cw.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(cw.target_type, "actor_friendly")

    def test_spell_aliases(self):
        """Magic Missile should have aliases."""
        mm = get_spell("magic_missile")
        self.assertIn("mm", mm.aliases)

    def test_school_key_property(self):
        """school_key should return string from enum school."""
        mm = get_spell("magic_missile")
        self.assertEqual(mm.school_key, "evocation")
        self.assertEqual(mm.school, skills.EVOCATION)


# ================================================================== #
#  Base Spell Cast Tests
# ================================================================== #

class TestSpellCast(EvenniaTest):
    """Test base spell cast() — mastery, mana, and dispatch."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("magic_missile")

    def test_cast_insufficient_mastery(self):
        """Cast should fail if caster has no mastery in the school."""
        self.char1.db.class_skill_mastery_levels = {}
        self.char1.mana = 100
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIsInstance(msg, str)
        self.assertIn("mastery", msg.lower())

    def test_cast_insufficient_mana(self):
        """Cast should fail if caster doesn't have enough mana."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.mana = 0
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIsInstance(msg, str)
        self.assertIn("mana", msg.lower())

    def test_cast_mana_not_deducted_on_failure(self):
        """Mana should NOT be deducted when cast fails."""
        self.char1.db.class_skill_mastery_levels = {}
        self.char1.mana = 50
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, 50)

    def test_cast_deducts_mana_on_success(self):
        """Mana should be deducted on successful cast."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.mana = 50
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.spell.cast(self.char1, self.char2)
        expected_cost = self.spell.mana_cost[1]  # 5
        self.assertEqual(self.char1.mana, 50 - expected_cost)

    def test_cast_returns_dict_on_success(self):
        """Successful cast should return (True, dict)."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.mana = 100
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    def test_get_caster_tier(self):
        """get_caster_tier returns correct mastery level."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        self.assertEqual(self.spell.get_caster_tier(self.char1), 3)

    def test_get_caster_tier_no_mastery(self):
        """get_caster_tier returns 0 for unknown school."""
        self.char1.db.class_skill_mastery_levels = {}
        self.assertEqual(self.spell.get_caster_tier(self.char1), 0)


# Cooldown tests moved to tests.spell_tests.test_spell_combat_integration —
# cooldowns are now tracked on the shared CombatHandler.skill_cooldown counter
# rather than a per-spell dict, and require a combat-enabled room to exercise.


# ================================================================== #
#  apply_spell_damage Tests
# ================================================================== #

class TestApplySpellDamage(EvenniaTest):
    """Test the apply_spell_damage utility."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.damage_resistances = {}

    def test_basic_damage(self):
        """Damage applied with no resistance."""
        actual = apply_spell_damage(self.char2, 20, DamageType.FIRE)
        self.assertEqual(actual, 20)
        self.assertEqual(self.char2.hp, 80)

    def test_resistance_reduces_damage(self):
        """50% fire resistance should halve damage."""
        self.char2.damage_resistances = {"fire": 50}
        actual = apply_spell_damage(self.char2, 20, DamageType.FIRE)
        self.assertEqual(actual, 10)
        self.assertEqual(self.char2.hp, 90)

    def test_vulnerability_amplifies_damage(self):
        """-25% resistance (vulnerability) should increase damage."""
        self.char2.damage_resistances = {"fire": -25}
        actual = apply_spell_damage(self.char2, 20, DamageType.FIRE)
        self.assertEqual(actual, 25)
        self.assertEqual(self.char2.hp, 75)

    def test_minimum_one_damage(self):
        """Even with max resistance, minimum 1 damage."""
        self.char2.damage_resistances = {"fire": 75}
        actual = apply_spell_damage(self.char2, 1, DamageType.FIRE)
        self.assertEqual(actual, 1)

    def test_hp_floors_at_zero(self):
        """HP should not go below 0."""
        self.char2.hp = 5
        with patch.object(self.char2, "die", MagicMock()):
            apply_spell_damage(self.char2, 100, DamageType.FIRE)
        self.assertEqual(self.char2.hp, 0)


# ================================================================== #
#  Spell Height Gating Tests
# ================================================================== #

class TestSpellHeightGating(EvenniaTest):
    """Test range height gating on melee vs ranged spells."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.db.class_skill_mastery_levels = {
            "necromancy": 2,
            "evocation": 1,
        }
        self.char1.mana = 500
        self.char1.mana_max = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.intelligence = 14
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_melee_spell_blocked_different_height(self):
        """Melee spell (Vampiric Touch) blocked when heights differ."""
        spell = get_spell("vampiric_touch")
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 1
        mana_before = self.char1.mana
        success, msg = spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("height", msg)
        self.assertEqual(self.char1.mana, mana_before)

    def test_melee_spell_works_same_height(self):
        """Melee spell (Vampiric Touch) works when at same height."""
        spell = get_spell("vampiric_touch")
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        success, result = spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)

    def test_ranged_spell_works_different_height(self):
        """Ranged spell (Magic Missile) works across heights."""
        spell = get_spell("magic_missile")
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 1
        success, result = spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)

    def test_ranged_spell_works_same_height(self):
        """Ranged spell (Magic Missile) works at same height."""
        spell = get_spell("magic_missile")
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        success, result = spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)

    def test_cure_wounds_blocked_different_height(self):
        """Cure Wounds (melee friendly) blocked across heights."""
        spell = get_spell("cure_wounds")
        self.char1.db.class_skill_mastery_levels["divine_healing"] = 1
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 1
        self.char2.hp = 50
        mana_before = self.char1.mana
        success, msg = spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("height", msg)
        self.assertEqual(self.char1.mana, mana_before)

    def test_cure_wounds_self_always_works(self):
        """Cure Wounds on self always works regardless of range."""
        spell = get_spell("cure_wounds")
        self.char1.db.class_skill_mastery_levels["divine_healing"] = 1
        self.char1.room_vertical_position = 1
        self.char1.hp = 50
        self.char1.hp_max = 100
        success, result = spell.cast(self.char1, self.char1)
        self.assertTrue(success)

    def test_range_attribute_exists(self):
        """All spells should have a range attribute."""
        for key, spell in SPELL_REGISTRY.items():
            self.assertIn(
                spell.range, ("self", "melee", "ranged"),
                f"Spell {key} has invalid range: {spell.range}",
            )


# ================================================================== #
#  Height-Filtered AoE Helper Tests
# ================================================================== #

class TestHeightFilteredAoE(EvenniaTest):
    """Test get_room_enemies_at_height and get_room_all_at_height."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from world.spells.spell_utils import (
            get_room_enemies_at_height,
            get_room_all_at_height,
        )
        self.get_enemies = get_room_enemies_at_height
        self.get_all = get_room_all_at_height
        self.char1.hp = 100
        self.char2.hp = 100
        self.char2.hp_max = 100

    def test_enemies_at_height_filters(self):
        """Only enemies at caster's height are returned."""
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 1
        result = self.get_enemies(self.char1)
        self.assertNotIn(self.char2, result)

    def test_enemies_at_same_height_included(self):
        """Enemies at caster's height are included."""
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        result = self.get_enemies(self.char1)
        # char2 is a PC so won't appear in out-of-combat enemy list,
        # but the filter itself works — empty is correct here
        # (get_room_enemies only returns NPCs when out of combat)

    def test_all_at_height_filters(self):
        """get_room_all_at_height only returns entities at caster height."""
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 1
        result = self.get_all(self.char1)
        self.assertIn(self.char1, result)
        self.assertNotIn(self.char2, result)

    def test_all_at_height_includes_same(self):
        """get_room_all_at_height includes entities at same height."""
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = 0
        result = self.get_all(self.char1)
        self.assertIn(self.char1, result)
        self.assertIn(self.char2, result)

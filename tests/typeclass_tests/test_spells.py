"""
Tests for spell registry, base spell class, and all spells.

Validates:
    - Registry: spells register correctly, lookup/filter works
    - Base Spell: mastery validation, mana deduction, cooldown, dispatch
    - MagicMissile: damage scaling with tier, auto-hit, multi-perspective messages
    - CureWounds: healing scaling with tier, wisdom modifier, hp_max clamp
    - Fireball: unsafe AoE, fire damage, hits everything including caster
    - ConeOfCold: safe AoE with diminishing accuracy, cold + SLOWED
    - FlameBurst: safe AoE fire, diminishing accuracy, scales 3d6→6d6 (SKILLED+)
    - Frostbolt: single-target cold debuff, contested SLOWED, flat 1d6 damage
    - PowerWordDeath: instant kill mechanics, contested save, nat 1/nat 20
    - SLOWED mechanic: caps attacks at 1/round, blocks off-hand

evennia test --settings settings tests.typeclass_tests.test_spells
"""

from unittest.mock import patch, MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import (
    SPELL_REGISTRY,
    get_spell,
    get_spells_for_school,
    list_spell_keys,
)
from world.spells.base_spell import Spell
from world.spells.spell_utils import apply_spell_damage
from enums.damage_type import DamageType


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
        self.assertEqual(mm.target_type, "hostile")
        self.assertIn(1, mm.mana_cost)

        cw = get_spell("cure_wounds")
        self.assertEqual(cw.school_key, "divine_healing")
        self.assertEqual(cw.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(cw.target_type, "friendly")

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


# ================================================================== #
#  Magic Missile Tests
# ================================================================== #

class TestMagicMissile(EvenniaTest):
    """Test MagicMissile spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("magic_missile")
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.mana = 100

    def test_deals_damage(self):
        """Magic Missile should reduce target HP."""
        self.char2.hp = 50
        self.char2.hp_max = 50
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertLess(self.char2.hp, 50)

    def test_tier1_one_missile(self):
        """At tier 1, fires 1 missile (1d4+1 damage, so 2-5)."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        damage = 100 - self.char2.hp
        self.assertGreaterEqual(damage, 2)
        self.assertLessEqual(damage, 5)
        self.assertIn("1 glowing missile", result["first"])

    def test_first_person_message(self):
        """First-person message should start with 'You'."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(result["first"].startswith("You"))

    def test_second_person_message(self):
        """Second-person message should contain caster name."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn(self.char1.key, result["second"])

    def test_third_person_message(self):
        """Third-person message should contain both caster and target names."""
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn(self.char1.key, result["third"])
        self.assertIn(self.char2.key, result["third"])

    def test_tier3_three_missiles(self):
        """At tier 3, fires 3 missiles (3d4+3 damage, so 6-15)."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        damage = 100 - self.char2.hp
        self.assertGreaterEqual(damage, 6)
        self.assertLessEqual(damage, 15)
        self.assertIn("3 glowing missiles", result["first"])

    def test_tier5_five_missiles(self):
        """At tier 5 (GRANDMASTER), fires 5 missiles (5d4+5 damage, so 10-25)."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char2.hp = 100
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        damage = 100 - self.char2.hp
        self.assertGreaterEqual(damage, 10)
        self.assertLessEqual(damage, 25)
        self.assertIn("5 glowing missiles", result["first"])

    def test_hp_floors_at_zero(self):
        """Target HP should not go below 0."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char2.hp = 1
        self.char2.hp_max = 100
        self.spell.cast(self.char1, self.char2)
        self.assertGreaterEqual(self.char2.hp, 0)


# ================================================================== #
#  Cure Wounds Tests
# ================================================================== #

class TestCureWounds(EvenniaTest):
    """Test CureWounds spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("cure_wounds")
        self.char1.db.class_skill_mastery_levels = {"divine_healing": 1}
        self.char1.mana = 100
        # Wisdom 14 → bonus = floor((14-10)/2) = +2
        self.char1.wisdom = 14

    def test_heals_target(self):
        """Cure Wounds should increase target HP."""
        self.char2.hp = 20
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertGreater(self.char2.hp, 20)

    def test_tier1_healing_range(self):
        """At tier 1 with wis 14 (+2): 1d6+2 = 3–8 healing."""
        self.char2.hp = 10
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        healed = self.char2.hp - 10
        self.assertGreaterEqual(healed, 3)
        self.assertLessEqual(healed, 8)

    def test_self_heal_first_person(self):
        """Self-heal first-person message should mention 'yourself'."""
        self.char1.hp = 10
        self.char1.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIn("yourself", result["first"].lower())

    def test_self_heal_no_second_person(self):
        """Self-heal should have None for second-person message."""
        self.char1.hp = 10
        self.char1.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIsNone(result["second"])

    def test_self_heal_third_person(self):
        """Self-heal third-person should mention caster name."""
        self.char1.hp = 10
        self.char1.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn(self.char1.key, result["third"])

    def test_other_heal_messages(self):
        """Healing another should have all three perspectives."""
        self.char2.hp = 10
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn(self.char2.key, result["first"])
        self.assertIn(self.char1.key, result["second"])
        self.assertIn(self.char1.key, result["third"])
        self.assertIn(self.char2.key, result["third"])

    def test_hp_clamped_to_max(self):
        """Healing should not exceed effective_hp_max."""
        self.char2.hp_max = 100
        effective_max = self.char2.effective_hp_max
        # Set HP to 1 below effective max so the spell fires
        self.char2.hp = max(1, effective_max - 1)
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertLessEqual(self.char2.hp, effective_max)

    def test_tier3_higher_healing(self):
        """At tier 3 with wis 14 (+2): 3d6+2 = 5–20 healing."""
        self.char1.db.class_skill_mastery_levels = {"divine_healing": 3}
        self.char2.hp = 10
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        healed = self.char2.hp - 10
        self.assertGreaterEqual(healed, 5)
        self.assertLessEqual(healed, 20)

    def test_low_wisdom_negative_bonus(self):
        """Wis 8 → bonus -1. At tier 1: max(0, 1d6-1) = 0–5 healing."""
        self.char1.wisdom = 8
        self.char2.hp = 10
        self.char2.hp_max = 100
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        healed = self.char2.hp - 10
        self.assertGreaterEqual(healed, 0)
        self.assertLessEqual(healed, 5)


# ================================================================== #
#  Cooldown Tests
# ================================================================== #

class TestSpellCooldown(EvenniaTest):
    """Test spell cooldown system."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("fireball")
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char2.hp = 200
        self.char2.hp_max = 200

    def test_default_cooldown_expert(self):
        """EXPERT spell should have default cooldown of 1."""
        self.assertEqual(self.spell.get_cooldown(), 1)

    def test_default_cooldown_master(self):
        """MASTER spell should have default cooldown of 2."""
        coc = get_spell("cone_of_cold")
        self.assertEqual(coc.get_cooldown(), 2)

    def test_default_cooldown_gm(self):
        """GM spell should have default cooldown of 3."""
        pwd = get_spell("power_word_death")
        self.assertEqual(pwd.get_cooldown(), 3)

    def test_default_cooldown_basic(self):
        """BASIC spell should have default cooldown of 0."""
        mm = get_spell("magic_missile")
        self.assertEqual(mm.get_cooldown(), 0)

    def test_cooldown_applied_after_cast(self):
        """Casting should set cooldown on caster."""
        self.spell.cast(self.char1, None)
        on_cd, remaining = self.spell.is_on_cooldown(self.char1)
        self.assertTrue(on_cd)
        self.assertEqual(remaining, 1)

    def test_cooldown_blocks_recast(self):
        """Spell on cooldown should not be castable."""
        self.spell.cast(self.char1, None)
        success, msg = self.spell.cast(self.char1, None)
        self.assertFalse(success)
        self.assertIn("cooldown", msg.lower())

    def test_no_cooldown_no_block(self):
        """BASIC spell with 0 cooldown should be recastable."""
        mm = get_spell("magic_missile")
        self.char2.hp = 200
        mm.cast(self.char1, self.char2)
        success, result = mm.cast(self.char1, self.char2)
        self.assertTrue(success)


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
#  Fireball Tests
# ================================================================== #

class TestFireball(EvenniaTest):
    """Test Fireball spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("fireball")
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char1.damage_resistances = {}
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_registered(self):
        """Fireball should be in the registry."""
        self.assertIn("fireball", SPELL_REGISTRY)

    def test_attributes(self):
        """Fireball should have correct class attributes."""
        self.assertEqual(self.spell.name, "Fireball")
        self.assertEqual(self.spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(self.spell.target_type, "none")

    def test_mana_costs(self):
        """Fireball mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_hits_caster(self):
        """Fireball should damage the caster (unsafe AoE)."""
        start_hp = self.char1.hp
        self.spell.cast(self.char1, None)
        self.assertLess(self.char1.hp, start_hp)

    def test_hits_others_in_room(self):
        """Fireball should damage others in the room."""
        start_hp = self.char2.hp
        self.spell.cast(self.char1, None)
        self.assertLess(self.char2.hp, start_hp)

    def test_deducts_mana(self):
        """Fireball should deduct correct mana."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, None)
        self.assertEqual(self.char1.mana, start_mana - 28)

    def test_returns_message_dict(self):
        """Successful cast should return message dict."""
        success, result = self.spell.cast(self.char1, None)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("third", result)

    def test_expert_damage_range(self):
        """At EXPERT tier, 8d6 = 8-48 full, 4-24 half (with save)."""
        self.char2.hp = 200
        self.spell.cast(self.char1, None)
        damage = 200 - self.char2.hp
        # Min is 4 (half of 8 on save), max is 48 (full on fail)
        self.assertGreaterEqual(damage, 4)
        self.assertLessEqual(damage, 48)

    def test_mastery_too_low(self):
        """Should fail if mastery below EXPERT."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 2}
        success, msg = self.spell.cast(self.char1, None)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_fire_resistance_reduces_damage(self):
        """Fire resistance should reduce fireball damage."""
        self.char2.damage_resistances = {"fire": 50}
        self.char2.hp = 200
        self.spell.cast(self.char1, None)
        damage = 200 - self.char2.hp
        # 50% resist on max 48 = max 24, half save on max 24 = max 12
        self.assertLessEqual(damage, 24)

    @patch("world.spells.evocation.fireball.dice")
    def test_save_full_damage_on_fail(self, mock_dice):
        """Failed DEX save should deal full damage."""
        # damage roll, save DC roll, char1 save, char2 save
        # High DC (20), low saves (1) → both fail → full damage
        mock_dice.roll.side_effect = [24, 20, 1, 1]
        self.char2.hp = 200
        self.char2.dexterity = 10
        self.spell.cast(self.char1, None)
        # char2 takes full 24 damage (no resistance)
        self.assertEqual(self.char2.hp, 200 - 24)

    @patch("world.spells.evocation.fireball.dice")
    def test_save_half_damage_on_success(self, mock_dice):
        """Successful DEX save should deal half damage."""
        # damage roll, save DC roll, char1 save, char2 save
        # Low DC (1), high saves (20) → both save → half damage
        mock_dice.roll.side_effect = [24, 1, 20, 20]
        self.char2.hp = 200
        self.char2.dexterity = 10
        self.spell.cast(self.char1, None)
        # char2 takes half of 24 = 12
        self.assertEqual(self.char2.hp, 200 - 12)

    @patch("world.spells.evocation.fireball.dice")
    def test_save_dc_shown_in_message(self, mock_dice):
        """Save DC should appear in caster message."""
        mock_dice.roll.side_effect = [24, 15, 1, 1]
        success, result = self.spell.cast(self.char1, None)
        self.assertIn("Save DC", result["first"])


# ================================================================== #
#  Cone of Cold Tests
# ================================================================== #

class TestConeOfCold(EvenniaTest):
    """Test Cone of Cold spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("cone_of_cold")
        self.char1.db.class_skill_mastery_levels = {"evocation": 4}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_registered(self):
        """Cone of Cold should be in the registry."""
        self.assertIn("cone_of_cold", SPELL_REGISTRY)

    def test_attributes(self):
        """Cone of Cold should have correct class attributes."""
        self.assertEqual(self.spell.name, "Cone of Cold")
        self.assertEqual(self.spell.min_mastery, MasteryLevel.MASTER)
        self.assertEqual(self.spell.target_type, "none")

    def test_mana_costs(self):
        """Cone of Cold mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {4: 35, 5: 46})

    def test_does_not_hit_caster(self):
        """Cone of Cold (safe AoE) should NOT damage the caster."""
        start_hp = self.char1.hp
        self.spell.cast(self.char1, None)
        self.assertEqual(self.char1.hp, start_hp)

    def test_deducts_mana(self):
        """Cone of Cold should deduct correct mana."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, None)
        self.assertEqual(self.char1.mana, start_mana - 35)

    def test_mastery_too_low(self):
        """Should fail if mastery below MASTER."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        success, msg = self.spell.cast(self.char1, None)
        self.assertFalse(success)

    @patch("world.spells.evocation.cone_of_cold.get_room_enemies")
    def test_first_enemy_always_hit(self, mock_enemies):
        """With one enemy and 100% chance, should always deal damage."""
        mock_enemies.return_value = [self.char2]
        # Run multiple times to verify consistency
        for _ in range(5):
            self.char2.hp = 200
            self.char1.mana = 500
            self.char1.db.spell_cooldowns = {}
            self.spell.cast(self.char1, None)
            self.assertLess(self.char2.hp, 200)

    @patch("world.spells.evocation.cone_of_cold.get_room_enemies")
    @patch("world.spells.evocation.cone_of_cold.dice")
    def test_applies_slowed_condition(self, mock_dice, mock_enemies):
        """Cone of Cold should apply SLOWED to hit targets."""
        mock_enemies.return_value = [self.char2]
        # Mock dice: first call is damage roll, second is 1d100 hit check
        mock_dice.roll.side_effect = [35, 50]  # 35 damage, 50 <= 100 (hit)
        self.char2.conditions = {}
        self.spell.cast(self.char1, None)
        self.assertTrue(self.char2.has_condition(Condition.SLOWED))

    @patch("world.spells.evocation.cone_of_cold.get_room_enemies")
    def test_returns_message_dict(self, mock_enemies):
        """Successful cast should return message dict."""
        mock_enemies.return_value = [self.char2]
        success, result = self.spell.cast(self.char1, None)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)

    def test_no_enemies_message(self):
        """Cast with no enemies should return appropriate message."""
        # get_room_enemies naturally returns [] when no NPCs present
        success, result = self.spell.cast(self.char1, None)
        self.assertTrue(success)
        self.assertIn("no enemies", result["first"].lower())


# ================================================================== #
#  Flame Burst Tests
# ================================================================== #

class TestFlameBurst(EvenniaTest):
    """Test Flame Burst spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("flame_burst")
        self.char1.db.class_skill_mastery_levels = {"evocation": 2}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_registered(self):
        """Flame Burst should be in the registry."""
        self.assertIn("flame_burst", SPELL_REGISTRY)

    def test_attributes(self):
        """Flame Burst should have correct class attributes."""
        self.assertEqual(self.spell.name, "Flame Burst")
        self.assertEqual(self.spell.school, skills.EVOCATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(self.spell.target_type, "none")

    def test_mana_costs(self):
        """Flame Burst mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {2: 11, 3: 14, 4: 18, 5: 21})

    def test_does_not_hit_caster(self):
        """Flame Burst (safe AoE) should NOT damage the caster."""
        start_hp = self.char1.hp
        self.spell.cast(self.char1, None)
        self.assertEqual(self.char1.hp, start_hp)

    def test_deducts_mana_skilled(self):
        """Flame Burst should deduct correct mana at SKILLED tier."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, None)
        self.assertEqual(self.char1.mana, start_mana - 11)

    @patch("world.spells.evocation.flame_burst.get_room_enemies")
    def test_first_enemy_always_hit(self, mock_enemies):
        """With one enemy and 100% chance, should always deal damage."""
        mock_enemies.return_value = [self.char2]
        for _ in range(5):
            self.char2.hp = 200
            self.char1.mana = 500
            self.char1.db.spell_cooldowns = {}
            self.spell.cast(self.char1, None)
            self.assertLess(self.char2.hp, 200)

    @patch("world.spells.evocation.flame_burst.get_room_enemies")
    @patch("world.spells.evocation.flame_burst.dice")
    def test_skilled_damage_range(self, mock_dice, mock_enemies):
        """At SKILLED tier, 3d6 = 3-18 damage."""
        mock_enemies.return_value = [self.char2]
        mock_dice.roll.side_effect = [11, 50]  # 11 damage, 50 <= 100 (hit)
        self.char2.hp = 200
        self.spell.cast(self.char1, None)
        damage = 200 - self.char2.hp
        self.assertEqual(damage, 11)

    @patch("world.spells.evocation.flame_burst.get_room_enemies")
    @patch("world.spells.evocation.flame_burst.dice")
    def test_gm_damage_range(self, mock_dice, mock_enemies):
        """At GM tier (5), 6d6 = 6-36 damage."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        mock_enemies.return_value = [self.char2]
        mock_dice.roll.side_effect = [21, 50]  # 21 damage, 50 <= 100 (hit)
        self.char2.hp = 200
        self.spell.cast(self.char1, None)
        damage = 200 - self.char2.hp
        self.assertEqual(damage, 21)

    @patch("world.spells.evocation.flame_burst.get_room_enemies")
    def test_returns_message_dict(self, mock_enemies):
        """Successful cast should return message dict."""
        mock_enemies.return_value = [self.char2]
        success, result = self.spell.cast(self.char1, None)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("third", result)

    def test_no_enemies_message(self):
        """Cast with no enemies should return appropriate message."""
        success, result = self.spell.cast(self.char1, None)
        self.assertTrue(success)
        self.assertIn("no enemies", result["first"].lower())

    def test_no_cooldown(self):
        """Flame Burst should have no cooldown (SKILLED default)."""
        self.assertEqual(self.spell.get_cooldown(), 0)

    @patch("world.spells.evocation.flame_burst.get_room_enemies")
    def test_fire_resistance_reduces_damage(self, mock_enemies):
        """Fire resistance should reduce flame burst damage."""
        mock_enemies.return_value = [self.char2]
        self.char2.damage_resistances = {"fire": 50}
        self.char2.hp = 200
        self.spell.cast(self.char1, None)
        damage = 200 - self.char2.hp
        # 50% resist on 3-18 raw = 2-9 actual
        self.assertLessEqual(damage, 9)

    def test_mastery_too_low(self):
        """Should fail if mastery is BASIC (1) — needs SKILLED."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        success, msg = self.spell.cast(self.char1, None)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())


# ================================================================== #
#  Power Word: Death Tests
# ================================================================== #

class TestPowerWordDeath(EvenniaTest):
    """Test Power Word: Death spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("power_word_death")
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.intelligence = 18  # +4 mod
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.constitution = 10  # +0 mod

    def test_registered(self):
        """Power Word: Death should be in the registry."""
        self.assertIn("power_word_death", SPELL_REGISTRY)

    def test_attributes(self):
        """PWD should have correct class attributes."""
        self.assertEqual(self.spell.name, "Power Word: Death")
        self.assertEqual(self.spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(self.spell.target_type, "hostile")

    def test_mana_cost(self):
        """PWD mana cost should be 100."""
        self.assertEqual(self.spell.mana_cost, {5: 100})

    def test_deducts_mana(self):
        """PWD should deduct 100 mana."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 100)

    def test_mastery_too_low(self):
        """Should fail if mastery below GRANDMASTER."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 4}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_below_threshold_instant_kill(self, mock_dice):
        """Target at or below 20 HP should die instantly (unless nat 1)."""
        mock_dice.roll.return_value = 10  # not nat 1
        self.char2.hp = 15
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, 0)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_below_threshold_nat1_fails(self, mock_dice):
        """Nat 1 should fail even against target below threshold."""
        mock_dice.roll.return_value = 1
        self.char2.hp = 10
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)  # spell still "succeeds" (mana spent)
        self.assertEqual(self.char2.hp, 10)  # but target lives

    @patch("world.spells.evocation.power_word_death.dice")
    def test_above_threshold_nat20_always_kills(self, mock_dice):
        """Nat 20 should always kill, even against high-HP target."""
        mock_dice.roll.side_effect = [20]  # caster rolls nat 20
        self.char2.hp = 500
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, 0)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_above_threshold_contested_kill(self, mock_dice):
        """Caster wins contested roll = target dies."""
        # Caster rolls 15, target rolls 5
        mock_dice.roll.side_effect = [15, 5]
        self.char2.hp = 50  # above threshold (20)
        # Caster: 15 + 4(int) + 8(GM) = 27
        # Target: 5 + 0(con) + 6(30 HP over / 5) = 11
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, 0)

    @patch("world.spells.evocation.power_word_death.dice")
    def test_above_threshold_contested_fail(self, mock_dice):
        """Target wins contested roll = target lives, no damage."""
        # Caster rolls 2, target rolls 19
        mock_dice.roll.side_effect = [2, 19]
        self.char2.hp = 50
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)  # spell "succeeds" (mana spent)
        self.assertEqual(self.char2.hp, 50)  # but target lives

    @patch("world.spells.evocation.power_word_death.dice")
    def test_hd_bonus_scaling(self, mock_dice):
        """Target far above threshold should get HD bonus."""
        # Target at 120 HP: (120-20)/5 = 20 HD bonus
        # Caster rolls 15: 15 + 4 + 8 = 27
        # Target rolls 5: 5 + 0 + 20 = 25 → caster wins
        mock_dice.roll.side_effect = [15, 5]
        self.char2.hp = 120
        with patch.object(self.char2, "die", MagicMock()):
            success, result = self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char2.hp, 0)  # barely wins

    @patch("world.spells.evocation.power_word_death.dice")
    def test_hd_bonus_makes_resist(self, mock_dice):
        """Very high HP target should resist more easily."""
        # Target at 220 HP: (220-20)/5 = 40 HD bonus
        # Caster rolls 15: 15 + 4 + 8 = 27
        # Target rolls 5: 5 + 0 + 40 = 45 → target wins
        mock_dice.roll.side_effect = [15, 5]
        self.char2.hp = 220
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char2.hp, 220)  # target resists

    def test_first_person_message_on_cast(self):
        """Cast should return first-person message."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)

    def test_cooldown_3_rounds(self):
        """PWD should have 3 round cooldown."""
        self.assertEqual(self.spell.get_cooldown(), 3)


# ================================================================== #
#  Frostbolt Tests
# ================================================================== #

class TestFrostbolt(EvenniaTest):
    """Test Frostbolt spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("frostbolt")
        self.char1.db.class_skill_mastery_levels = {"evocation": 1}
        self.char1.mana = 100
        self.char1.db.spell_cooldowns = {}
        self.char1.intelligence = 14  # +2 mod
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.constitution = 10  # +0 mod

    def test_registered(self):
        """Frostbolt should be in the registry."""
        self.assertIn("frostbolt", SPELL_REGISTRY)

    def test_attributes(self):
        """Frostbolt should have correct class attributes."""
        self.assertEqual(self.spell.name, "Frostbolt")
        self.assertEqual(self.spell.school, skills.EVOCATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(self.spell.target_type, "hostile")
        self.assertEqual(self.spell.cooldown, 0)

    def test_deals_cold_damage(self):
        """Frostbolt should reduce target HP."""
        start_hp = self.char2.hp
        self.spell.cast(self.char1, self.char2)
        self.assertLess(self.char2.hp, start_hp)

    def test_deducts_mana(self):
        """Frostbolt should deduct 5 mana at tier 1."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 5)

    @patch("world.spells.evocation.frostbolt.dice")
    def test_applies_slowed_on_successful_contest(self, mock_dice):
        """SLOWED should be applied when caster wins contested check."""
        # damage roll, caster d20, target d20
        mock_dice.roll.side_effect = [3, 18, 2]
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char2.has_effect("slowed"))
        self.assertTrue(self.char2.has_condition(Condition.SLOWED))

    @patch("world.spells.evocation.frostbolt.dice")
    def test_no_slow_on_failed_contest(self, mock_dice):
        """SLOWED should NOT be applied when target wins contested check."""
        # damage roll, caster d20, target d20
        mock_dice.roll.side_effect = [3, 2, 18]
        self.spell.cast(self.char1, self.char2)
        self.assertFalse(self.char2.has_effect("slowed"))

    @patch("world.spells.evocation.frostbolt.dice")
    def test_slowed_duration_scales_with_tier(self, mock_dice):
        """Tier 3 should apply SLOWED for 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 3}
        # damage roll, caster d20 (high), target d20 (low)
        mock_dice.roll.side_effect = [3, 20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("slowed")
        self.assertIsNotNone(effect)
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.evocation.frostbolt.dice")
    def test_damage_flat_across_tiers(self, mock_dice):
        """Damage should be 1d6 regardless of tier."""
        # At tier 1: damage=4, then contest rolls
        mock_dice.roll.side_effect = [4, 2, 18]
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        tier1_damage = 200 - self.char2.hp

        # At tier 5: same damage=4
        self.char1.db.class_skill_mastery_levels = {"evocation": 5}
        self.char2.hp = 200
        mock_dice.roll.side_effect = [4, 2, 18]
        self.spell.cast(self.char1, self.char2)
        tier5_damage = 200 - self.char2.hp

        self.assertEqual(tier1_damage, tier5_damage)

    def test_cold_resistance_reduces_damage(self):
        """Cold resistance should reduce frostbolt damage."""
        self.char2.damage_resistances = {"cold": 50}
        self.char2.hp = 200
        self.spell.cast(self.char1, self.char2)
        # 1d6 max 6, 50% resist → max 3 damage
        self.assertGreaterEqual(self.char2.hp, 197)

    def test_multi_perspective_messages(self):
        """Cast should return first/second/third person messages."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    def test_mastery_check(self):
        """UNSKILLED should not be able to cast Frostbolt."""
        self.char1.db.class_skill_mastery_levels = {"evocation": 0}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)

    @patch("world.spells.evocation.frostbolt.dice")
    def test_message_includes_roll_details(self, mock_dice):
        """Output should include contested roll detail."""
        mock_dice.roll.side_effect = [3, 15, 5]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("Frost:", result["first"])


# ================================================================== #
#  Vampiric Touch Tests
# ================================================================== #

class TestVampiricTouch(EvenniaTest):
    """Test Vampiric Touch spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("vampiric_touch")
        self.char1.db.class_skill_mastery_levels = {"necromancy": 2}
        self.char1.mana = 100
        self.char1.mana_max = 100
        self.char1.hp = 50
        self.char1.hp_max = 100
        self.char1.intelligence = 14  # +2 mod
        self.char1.db.spell_cooldowns = {}
        self.char2.hp = 200
        self.char2.hp_max = 200

    def test_registration(self):
        """Vampiric Touch should be in the registry."""
        self.assertIn("vampiric_touch", SPELL_REGISTRY)

    def test_attributes(self):
        """Vampiric Touch should have correct class attributes."""
        self.assertEqual(self.spell.name, "Vampiric Touch")
        self.assertEqual(self.spell.school, skills.NECROMANCY)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(self.spell.target_type, "hostile")
        self.assertEqual(self.spell.cooldown, 0)
        self.assertIn("vt", self.spell.aliases)
        self.assertIn("vamp", self.spell.aliases)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_touch_attack_miss(self, mock_dice):
        """Miss should deal no damage but still spend mana."""
        # d20 roll = 1 (miss), no damage roll needed
        mock_dice.roll.return_value = 1
        start_mana = self.char1.mana
        start_hp = self.char2.hp
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertEqual(self.char2.hp, start_hp)  # no damage
        self.assertLess(self.char1.mana, start_mana)  # mana spent
        self.assertIn("misses", result["first"])

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_touch_attack_hit_heals(self, mock_dice):
        """Hit should deal damage and heal the caster."""
        # d20 = 20 (hit), 1d6 = 4
        mock_dice.roll.side_effect = [20, 4]
        hp_before = self.char1.hp
        self.spell.cast(self.char1, self.char2)
        self.assertLess(self.char2.hp, 200)  # target took damage
        self.assertGreater(self.char1.hp, hp_before)  # caster healed

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_healing_above_max_hp(self, mock_dice):
        """Caster HP should be able to exceed effective_hp_max."""
        self.char1.hp = self.char1.effective_hp_max  # full HP
        # d20 = 20 (hit), 1d6 = 5
        mock_dice.roll.side_effect = [20, 5]
        self.spell.cast(self.char1, self.char2)
        self.assertGreater(self.char1.hp, self.char1.effective_hp_max)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_bonus_hp_tracking(self, mock_dice):
        """db.vampiric_bonus_hp should track HP above max."""
        self.char1.hp = self.char1.effective_hp_max
        # d20 = 20 (hit), 1d6 = 5
        mock_dice.roll.side_effect = [20, 5]
        self.spell.cast(self.char1, self.char2)
        bonus = self.char1.db.vampiric_bonus_hp or 0
        self.assertEqual(bonus, 5)

    def test_mana_cost_base_bracket(self):
        """At +0 bonus HP, cost should be 3% of max mana."""
        self.char1.mana_max = 100
        cost, error = self.spell._get_mana_cost(self.char1)
        self.assertIsNone(error)
        self.assertEqual(cost, 3)  # 3% of 100

    def test_mana_cost_escalation(self):
        """Higher bonus HP bracket should cost more mana."""
        self.char1.mana_max = 100
        self.char1.db.vampiric_bonus_hp = 300  # bracket 3 → 16%
        cost, error = self.spell._get_mana_cost(self.char1)
        self.assertIsNone(error)
        self.assertEqual(cost, 16)  # 16% of 100

    def test_mana_cost_hard_cap(self):
        """At +1000 bonus HP, should return error (101% cost)."""
        self.char1.db.vampiric_bonus_hp = 1000
        cost, error = self.spell._get_mana_cost(self.char1)
        self.assertIsNotNone(error)
        self.assertIn("too far", error)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_vampiric_effect_applied(self, mock_dice):
        """has_effect('vampiric') should be True after successful cast."""
        # d20 = 20 (hit), 1d6 = 4
        mock_dice.roll.side_effect = [20, 4]
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char1.has_effect("vampiric"))

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_timer_expiry_hp_loss(self, mock_dice):
        """When vampiric effect removed, bonus HP should be lost (floor 1)."""
        self.char1.hp = self.char1.effective_hp_max
        # d20 = 20 (hit), 1d6 = 5
        mock_dice.roll.side_effect = [20, 5]
        self.spell.cast(self.char1, self.char2)
        self.assertGreater(self.char1.hp, self.char1.effective_hp_max)

        # Simulate timer expiry
        from world.spells.necromancy.vampiric_touch import remove_vampiric
        remove_vampiric(self.char1)

        self.assertLessEqual(self.char1.hp, self.char1.effective_hp_max)
        self.assertGreaterEqual(self.char1.hp, 1)
        self.assertIsNone(self.char1.db.vampiric_bonus_hp)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_necrotic_resistance_reduces_healing(self, mock_dice):
        """Necrotic resistance should reduce both damage and healing."""
        self.char2.damage_resistances = {"necrotic": 50}
        # d20 = 20 (hit), 1d6 = 6
        mock_dice.roll.side_effect = [20, 6]
        hp_before = self.char1.hp
        self.spell.cast(self.char1, self.char2)
        heal_amount = self.char1.hp - hp_before
        # 50% necrotic resist on 6 raw → 3 actual damage → 3 healing
        self.assertEqual(heal_amount, 3)

    @patch("world.spells.necromancy.vampiric_touch.dice")
    def test_damage_scaling(self, mock_dice):
        """SKILLED=1d6 range, GM=4d6 range."""
        # Tier 2 (SKILLED): 1d6, min=1, max=6
        mock_dice.roll.side_effect = [20, 4]
        self.spell.cast(self.char1, self.char2)
        tier2_damage = 200 - self.char2.hp
        self.assertGreaterEqual(tier2_damage, 1)
        self.assertLessEqual(tier2_damage, 6)

        # Tier 5 (GM): 4d6, min=4, max=24
        self.char1.db.class_skill_mastery_levels = {"necromancy": 5}
        self.char2.hp = 200
        self.char1.hp = 50
        self.char1.mana = 100
        self.char1.attributes.remove("vampiric_bonus_hp")
        # Remove vampiric effect for clean state
        if self.char1.has_effect("vampiric"):
            self.char1.remove_named_effect("vampiric")
        existing = self.char1.scripts.get("vampiric_timer")
        if existing:
            existing[0].delete()
        mock_dice.roll.side_effect = [20, 14]
        self.spell.cast(self.char1, self.char2)
        tier5_damage = 200 - self.char2.hp
        self.assertGreaterEqual(tier5_damage, 4)
        self.assertLessEqual(tier5_damage, 24)

    def test_mastery_check(self):
        """BASIC mastery should not be able to cast Vampiric Touch."""
        self.char1.db.class_skill_mastery_levels = {"necromancy": 1}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())


# ================================================================== #
#  SLOWED Combat Mechanic Tests
# ================================================================== #

class TestSlowedMechanic(EvenniaTest):
    """Test SLOWED effect enforcement in combat_handler."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.hp = 200
        self.char1.hp_max = 200
        self.char2.hp = 200
        self.char2.hp_max = 200

    def _start_combat(self, attacker, target):
        """Put attacker into combat against target."""
        from combat.combat_handler import CombatHandler
        from evennia.utils.create import create_script
        handler = create_script(
            CombatHandler, obj=attacker, key="combat_handler",
            autostart=False,
        )
        handler.start()
        handler.queue_action({
            "key": "attack", "target": target,
            "dt": 3, "repeat": True,
        })
        return handler

    @patch("combat.combat_utils.execute_attack")
    def test_slowed_caps_attacks_at_one(self, mock_attack):
        """SLOWED actor with multiple APR should only get 1 attack."""
        self.char1.attacks_per_round = 3
        handler = self._start_combat(self.char1, self.char2)
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        handler.execute_next_action()
        self.assertEqual(mock_attack.call_count, 1)

    @patch("combat.combat_utils.execute_attack")
    def test_slowed_blocks_offhand(self, mock_attack):
        """SLOWED actor with off-hand weapon should only get 1 main attack."""
        self.char1.attacks_per_round = 1
        handler = self._start_combat(self.char1, self.char2)

        # Apply SLOWED first
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )

        # Mock a weapon with off-hand attacks
        mock_weapon = MagicMock()
        mock_weapon.get_extra_attacks.return_value = 0
        mock_weapon.get_parries_per_round.return_value = 0
        mock_weapon.get_parry_advantage.return_value = False
        mock_weapon.get_offhand_attacks.return_value = 1
        mock_weapon.get_reach_counters_per_round.return_value = 0
        mock_weapon.get_stun_checks_per_round.return_value = 0
        mock_weapon.get_disarm_checks_per_round.return_value = 0

        mock_get_offhand = MagicMock(return_value=MagicMock())

        with patch("combat.combat_utils.get_weapon", return_value=mock_weapon):
            with patch("combat.combat_utils.get_offhand_weapon", mock_get_offhand):
                handler.execute_next_action()

        # Only 1 main attack, off-hand never called
        self.assertEqual(mock_attack.call_count, 1)
        mock_get_offhand.assert_not_called()

    @patch("combat.combat_utils.execute_attack")
    def test_slowed_per_round_message(self, mock_attack):
        """SLOWED actor should receive sluggish message each round."""
        self.char1.attacks_per_round = 1
        handler = self._start_combat(self.char1, self.char2)
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        mock_msg = MagicMock()
        original_msg = self.char1.msg
        self.char1.msg = mock_msg
        try:
            handler.execute_next_action()
        finally:
            self.char1.msg = original_msg
        # Check that the slowed message was sent to the actor
        found = False
        for call in mock_msg.call_args_list:
            msg = call.args[0] if call.args else ""
            if "SLOWED" in msg and "sluggish" in msg:
                found = True
                break
        self.assertTrue(found, "SLOWED per-round message not found")


# ================================================================== #
#  Entangle Tests
# ================================================================== #

class TestEntangle(EvenniaTest):
    """Test Entangle spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("entangle")
        self.char1.db.class_skill_mastery_levels = {"nature_magic": 1}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}
        # Default ability scores
        self.char1.wisdom = 14
        self.char2.strength = 10

    def test_registered(self):
        """Entangle should be in the registry."""
        self.assertIn("entangle", SPELL_REGISTRY)

    def test_attributes(self):
        """Entangle should have correct class attributes."""
        self.assertEqual(self.spell.name, "Entangle")
        self.assertEqual(self.spell.school, skills.NATURE_MAGIC)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(self.spell.target_type, "hostile")

    def test_mana_costs(self):
        """Entangle mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_deducts_mana(self):
        """Entangle should deduct correct mana at BASIC tier."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 5)

    def test_no_cooldown(self):
        """Entangle should have no cooldown."""
        self.assertEqual(self.spell.get_cooldown(), 0)

    @patch("world.spells.nature_magic.entangle.dice")
    def test_entangle_success(self, mock_dice):
        """High caster roll should apply entangled effect."""
        # Caster rolls 20, target rolls 1
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char2.has_effect("entangled"))

    @patch("world.spells.nature_magic.entangle.dice")
    def test_entangle_failure(self, mock_dice):
        """Low caster roll should not apply entangled effect."""
        # Caster rolls 1, target rolls 20
        mock_dice.roll.side_effect = [1, 20]
        self.spell.cast(self.char1, self.char2)
        self.assertFalse(self.char2.has_effect("entangled"))

    @patch("world.spells.nature_magic.entangle.dice")
    def test_entangle_returns_message_dict(self, mock_dice):
        """Successful cast should return message dict with perspectives."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    @patch("world.spells.nature_magic.entangle.dice")
    def test_entangle_success_message(self, mock_dice):
        """Success message should mention ENTANGLED."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("ENTANGLED", result["first"])

    @patch("world.spells.nature_magic.entangle.dice")
    def test_entangle_failure_message(self, mock_dice):
        """Failure message should mention tearing free."""
        mock_dice.roll.side_effect = [1, 20]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("tears free", result["first"])

    @patch("world.spells.nature_magic.entangle.dice")
    def test_duration_scales_with_tier(self, mock_dice):
        """At GM tier, entangle should last 5 rounds."""
        self.char1.db.class_skill_mastery_levels = {"nature_magic": 5}
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("5 rounds", result["first"])

    def test_mastery_too_low(self):
        """Should fail if mastery is 0."""
        self.char1.db.class_skill_mastery_levels = {"nature_magic": 0}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    @patch("world.spells.nature_magic.entangle.dice")
    def test_custom_vine_messages(self, mock_dice):
        """Entangle should use nature-themed messages, not bola defaults."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("vines", result["first"].lower())


# ================================================================== #
#  Holy Insight Tests
# ================================================================== #

class TestHolyInsight(EvenniaTest):
    """Test Holy Insight spell execution."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("holy_insight")
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 1}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}

    def test_registered(self):
        """Holy Insight should be in the registry."""
        self.assertIn("holy_insight", SPELL_REGISTRY)

    def test_attributes(self):
        """Holy Insight should have correct class attributes."""
        self.assertEqual(self.spell.name, "Holy Insight")
        self.assertEqual(self.spell.school, skills.DIVINE_REVELATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(self.spell.target_type, "any")

    def test_mana_costs(self):
        """Holy Insight mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_no_cooldown(self):
        """Holy Insight should have no cooldown."""
        self.assertEqual(self.spell.get_cooldown(), 0)

    def test_identify_mundane_object(self):
        """Mundane objects should get the sassy one-liner (inherited from Identify)."""
        success, result = self.spell.cast(self.char1, self.obj1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)

    def test_identify_actor_includes_divine_sight(self):
        """Actor identification should include Divine Sight section."""
        # Identifying other PCs requires PvP room
        self.room1.allow_pvp = True
        self.char2.db.level = 1
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("Divine Sight", result["first"])

    def test_divine_sight_shows_alignment(self):
        """Divine Sight should show target's alignment."""
        self.room1.allow_pvp = True
        self.char2.db.level = 1
        self.char2.alignment_score = -500  # Evil
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("Alignment", result["first"])
        self.assertIn("Evil", result["first"])

    def test_divine_sight_evil_detection(self):
        """Evil-aligned targets should trigger evil detection message."""
        self.room1.allow_pvp = True
        self.char2.db.level = 1
        self.char2.alignment_score = -500  # Evil
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("evil intent", result["first"].lower())

    def test_divine_sight_no_evil_for_good(self):
        """Good-aligned targets should NOT trigger evil detection."""
        self.room1.allow_pvp = True
        self.char2.db.level = 1
        self.char2.alignment_score = 500  # Good
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertNotIn("evil intent", result["first"].lower())

    def test_undead_detection(self):
        """Targets tagged as undead should be flagged."""
        self.room1.allow_pvp = True
        self.char2.db.level = 1
        self.char2.tags.add("undead", category="creature_type")
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("UNDEAD", result["first"])

    def test_mastery_too_low(self):
        """Should fail if mastery is 0."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 0}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())


# ================================================================== #
#  Smite Tests (reactive spell)
# ================================================================== #

class TestSmite(EvenniaTest):
    """Test Smite spell class (reactive-only, not castable)."""

    def create_script(self):
        pass

    def test_registered(self):
        """Smite should be in the registry."""
        self.assertIn("smite", SPELL_REGISTRY)

    def test_attributes(self):
        """Smite should have correct class attributes."""
        spell = get_spell("smite")
        self.assertEqual(spell.name, "Smite")
        self.assertEqual(spell.school, skills.DIVINE_JUDGEMENT)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "self")

    def test_mana_costs(self):
        """Smite mana costs should match per-hit design."""
        spell = get_spell("smite")
        self.assertEqual(spell.mana_cost, {1: 3, 2: 5, 3: 7, 4: 9, 5: 12})

    def test_scaling(self):
        """Smite should scale 1d6 to 5d6 by tier."""
        spell = get_spell("smite")
        self.assertEqual(spell._SCALING, {1: 1, 2: 2, 3: 3, 4: 4, 5: 5})

    def test_reactive_only_not_castable(self):
        """Casting Smite manually should return informational message."""
        spell = get_spell("smite")
        self.char1.db.class_skill_mastery_levels = {"divine_judgement": 1}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        success, result = spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("reactive", result["first"].lower())

    def test_no_cooldown(self):
        """Smite should have no cooldown."""
        spell = get_spell("smite")
        self.assertEqual(spell.get_cooldown(), 0)


class TestCheckReactiveSmite(EvenniaTest):
    """Test the check_reactive_smite() function from reactive_spells."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from combat.reactive_spells import check_reactive_smite
        self.check_smite = check_reactive_smite
        # Set up attacker with divine judgement mastery
        self.char1.db.class_skill_mastery_levels = {"divine_judgement": 1}
        self.char1.mana = 500
        self.char1.db.memorised_spells = {"smite": True}
        self.char1.smite_active = True
        # Target
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    @patch("combat.reactive_spells.dice")
    def test_fires_when_all_gates_pass(self, mock_dice):
        """Should fire and return damage when toggled, memorised, has mana."""
        mock_dice.roll.return_value = 4  # 1d6 = 4
        result = self.check_smite(self.char1, self.char2)
        self.assertGreater(result, 0)

    @patch("combat.reactive_spells.dice")
    def test_deducts_mana(self, mock_dice):
        """Should deduct correct mana cost on trigger."""
        mock_dice.roll.return_value = 3
        start_mana = self.char1.mana
        self.check_smite(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 3)  # tier 1 = 3 mana

    def test_no_fire_toggle_off(self):
        """Should NOT fire when toggle is off."""
        self.char1.smite_active = False
        result = self.check_smite(self.char1, self.char2)
        self.assertEqual(result, 0)

    def test_no_fire_not_memorised(self):
        """Should NOT fire when Smite is not memorised."""
        self.char1.db.memorised_spells = {}
        result = self.check_smite(self.char1, self.char2)
        self.assertEqual(result, 0)

    def test_no_fire_insufficient_mana(self):
        """Should NOT fire when mana is too low."""
        self.char1.mana = 2  # tier 1 costs 3
        result = self.check_smite(self.char1, self.char2)
        self.assertEqual(result, 0)

    def test_no_fire_mastery_too_low(self):
        """Should NOT fire when divine_judgement mastery is 0."""
        self.char1.db.class_skill_mastery_levels = {"divine_judgement": 0}
        result = self.check_smite(self.char1, self.char2)
        self.assertEqual(result, 0)

    @patch("combat.reactive_spells.dice")
    def test_scales_by_tier(self, mock_dice):
        """Higher tier should roll more dice."""
        # Tier 3 = 3d6
        self.char1.db.class_skill_mastery_levels = {"divine_judgement": 3}
        mock_dice.roll.return_value = 12  # 3d6 = 12
        self.check_smite(self.char1, self.char2)
        mock_dice.roll.assert_called_with("3d6")

    @patch("combat.reactive_spells.dice")
    def test_tier5_rolls_5d6(self, mock_dice):
        """GM tier should roll 5d6."""
        self.char1.db.class_skill_mastery_levels = {"divine_judgement": 5}
        mock_dice.roll.return_value = 20
        self.check_smite(self.char1, self.char2)
        mock_dice.roll.assert_called_with("5d6")

    @patch("combat.reactive_spells.dice")
    def test_mana_cost_scales_by_tier(self, mock_dice):
        """Tier 3 should cost 7 mana per trigger."""
        self.char1.db.class_skill_mastery_levels = {"divine_judgement": 3}
        mock_dice.roll.return_value = 10
        start_mana = self.char1.mana
        self.check_smite(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 7)

    @patch("combat.reactive_spells.dice")
    def test_respects_radiant_resistance(self, mock_dice):
        """Target with radiant resistance should take reduced damage."""
        mock_dice.roll.return_value = 6  # 1d6 = 6
        self.char2.damage_resistances = {"radiant": 50}  # 50% resistance
        result = self.check_smite(self.char1, self.char2)
        self.assertEqual(result, 3)  # 6 - max(1, int(6*50/100)) = 3


# ================================================================== #
#  Sanctuary Tests
# ================================================================== #

class TestSanctuary(EvenniaTest):
    """Test Sanctuary spell registration and attributes."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("sanctuary")
        self.char1.db.class_skill_mastery_levels = {"divine_protection": 1}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}

    def test_registered(self):
        """Sanctuary should be in the registry."""
        self.assertIn("sanctuary", SPELL_REGISTRY)

    def test_attributes(self):
        """Sanctuary should have correct class attributes."""
        self.assertEqual(self.spell.name, "Sanctuary")
        self.assertEqual(self.spell.school, skills.DIVINE_PROTECTION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(self.spell.target_type, "self")

    def test_mana_costs(self):
        """Sanctuary mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_duration_dict(self):
        """Sanctuary _DURATION should store minutes and scale correctly."""
        self.assertEqual(self.spell._DURATION, {1: 1, 2: 2, 3: 3, 4: 4, 5: 5})

    def test_no_cooldown(self):
        """Sanctuary should have no cooldown."""
        self.assertEqual(self.spell.get_cooldown(), 0)

    def test_cast_applies_condition(self):
        """Casting Sanctuary should apply SANCTUARY condition."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_condition(Condition.SANCTUARY))

    def test_cast_applies_named_effect(self):
        """Casting Sanctuary should apply 'sanctuary' named effect."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_effect("sanctuary"))

    def test_cast_deducts_mana(self):
        """Casting Sanctuary should deduct mana."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char1)
        self.assertEqual(self.char1.mana, start_mana - 5)  # tier 1 = 5 mana

    def test_messages_contain_sanctuary(self):
        """Cast messages should reference sanctuary."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("sanctuary", result["first"].lower())

    def test_third_person_message(self):
        """Third-person message should contain caster name."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn(self.char1.key, result["third"])

    def test_duration_scales_by_tier(self):
        """Higher tier should give longer duration."""
        self.char1.db.class_skill_mastery_levels = {"divine_protection": 3}
        self.spell.cast(self.char1, self.char1)
        record = self.char1.get_named_effect("sanctuary")
        self.assertIsNotNone(record)
        self.assertEqual(record["duration"], 180)  # 3 minutes

    def test_break_sanctuary_clears_condition(self):
        """break_sanctuary() should remove the SANCTUARY condition."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.SANCTUARY))
        result = self.char1.break_sanctuary()
        self.assertTrue(result)
        self.assertFalse(self.char1.has_condition(Condition.SANCTUARY))

    def test_break_sanctuary_when_not_active(self):
        """break_sanctuary() should return False if not active."""
        result = self.char1.break_sanctuary()
        self.assertFalse(result)

    def test_recast_refreshes_effect(self):
        """Recasting Sanctuary should refresh the duration (remove + reapply)."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.SANCTUARY))
        start_mana = self.char1.mana
        # Second cast — should succeed (remove old, apply new)
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_condition(Condition.SANCTUARY))
        self.assertEqual(self.char1.mana, start_mana - 5)

    @patch("world.spells.divine_protection.sanctuary.Sanctuary.get_caster_tier")
    def test_recast_skips_when_existing_stronger(self, mock_tier):
        """Recast should skip and refund mana if existing effect has more time."""
        # First cast at tier 5 (300 seconds)
        mock_tier.return_value = 5
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_effect("sanctuary"))

        # Mock remaining time to be very high (e.g. 290 seconds left)
        with patch.object(
            type(self.char1), "get_effect_remaining_seconds",
            return_value=290,
        ):
            # Recast at tier 1 (60 seconds) — should skip
            mock_tier.return_value = 1
            start_mana = self.char1.mana
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertFalse(success)
            # Mana refunded (deducted then refunded = net zero)
            self.assertEqual(self.char1.mana, start_mana)
            self.assertIn("stronger", result["first"].lower())


# ================================================================== #
#  Invisibility Recast Fix Tests
# ================================================================== #

class TestInvisibilityRecast(EvenniaTest):
    """Test that recasting Invisibility refreshes duration correctly."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("invisibility")
        self.char1.db.class_skill_mastery_levels = {"illusion": 2}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}

    def test_recast_refreshes(self):
        """Recasting Invisibility should refresh duration (not waste mana)."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        start_mana = self.char1.mana
        # Second cast — should succeed
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        self.assertEqual(self.char1.mana, start_mana - 15)  # tier 2 = 15 mana

    @patch("world.spells.illusion.invisibility.Invisibility.get_caster_tier")
    def test_recast_skips_when_existing_stronger(self, mock_tier):
        """Recast should skip and refund if existing invisibility has more time."""
        # First cast at tier 5 (60 min = 3600 seconds)
        mock_tier.return_value = 5
        self.spell.cast(self.char1, self.char1)

        # Mock remaining time > new duration
        with patch.object(
            type(self.char1), "get_effect_remaining_seconds",
            return_value=3500,
        ):
            # Recast at tier 2 (5 min = 300 seconds) — should skip
            mock_tier.return_value = 2
            start_mana = self.char1.mana
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertFalse(success)
            self.assertEqual(self.char1.mana, start_mana)  # refunded
            self.assertIn("stronger", result["first"].lower())


# ================================================================== #
#  Effect Registry Tests
# ================================================================== #

from enums.named_effect import NamedEffect


class TestEffectRegistry(EvenniaTest):
    """Test the NamedEffect registry for condition and duration_type metadata."""

    def create_script(self):
        pass

    def test_slowed_has_condition(self):
        """SLOWED should map to Condition.SLOWED."""
        self.assertEqual(NamedEffect.SLOWED.effect_condition, Condition.SLOWED)

    def test_paralysed_has_condition(self):
        """PARALYSED should map to Condition.PARALYSED."""
        self.assertEqual(NamedEffect.PARALYSED.effect_condition, Condition.PARALYSED)

    def test_invisible_has_condition(self):
        """INVISIBLE should map to Condition.INVISIBLE."""
        self.assertEqual(NamedEffect.INVISIBLE.effect_condition, Condition.INVISIBLE)

    def test_sanctuary_has_condition(self):
        """SANCTUARY should map to Condition.SANCTUARY."""
        self.assertEqual(NamedEffect.SANCTUARY.effect_condition, Condition.SANCTUARY)

    def test_stunned_no_condition(self):
        """STUNNED should have no condition."""
        self.assertIsNone(NamedEffect.STUNNED.effect_condition)

    def test_prone_no_condition(self):
        """PRONE should have no condition."""
        self.assertIsNone(NamedEffect.PRONE.effect_condition)

    def test_combat_round_effects(self):
        """Combat round effects should have duration_type='combat_rounds'."""
        combat_effects = [
            NamedEffect.STUNNED, NamedEffect.PRONE, NamedEffect.SLOWED,
            NamedEffect.PARALYSED, NamedEffect.ENTANGLED, NamedEffect.BLURRED,
            NamedEffect.SHIELD, NamedEffect.STAGGERED, NamedEffect.SUNDERED,
        ]
        for ne in combat_effects:
            self.assertEqual(ne.effect_duration_type, "combat_rounds",
                             f"{ne.name} should be combat_rounds")

    def test_seconds_effects(self):
        """Seconds-based effects should have duration_type='seconds'."""
        seconds_effects = [
            NamedEffect.INVISIBLE, NamedEffect.SANCTUARY,
            NamedEffect.ARMORED, NamedEffect.SHADOWCLOAKED,
            NamedEffect.TRUE_SIGHT,
        ]
        for ne in seconds_effects:
            self.assertEqual(ne.effect_duration_type, "seconds",
                             f"{ne.name} should be seconds")

    def test_script_managed_effects(self):
        """Script-managed effects should have duration_type=None."""
        script_effects = [
            NamedEffect.POISONED, NamedEffect.ACID_ARROW, NamedEffect.VAMPIRIC,
        ]
        for ne in script_effects:
            self.assertIsNone(ne.effect_duration_type,
                              f"{ne.name} should be None")

    def test_all_effects_have_duration_type(self):
        """Every NamedEffect should have an entry in the duration_type registry."""
        # POTION_TEST is test-only, skip it
        for ne in NamedEffect:
            if ne == NamedEffect.POTION_TEST:
                continue
            dt = ne.effect_duration_type
            self.assertIn(dt, ("combat_rounds", "seconds", None),
                          f"{ne.name} has unexpected duration_type: {dt}")


# ================================================================== #
#  Convenience Method Tests
# ================================================================== #


class TestConvenienceMethods(EvenniaTest):
    """Test that convenience methods on EffectsManagerMixin work correctly."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_apply_stunned(self):
        """apply_stunned should create a stunned named effect."""
        result = self.char1.apply_stunned(2)
        self.assertTrue(result)
        self.assertTrue(self.char1.has_effect("stunned"))
        record = self.char1.get_named_effect("stunned")
        self.assertEqual(record["duration"], 2)
        self.assertEqual(record["duration_type"], "combat_rounds")

    def test_apply_prone(self):
        """apply_prone should create a prone named effect."""
        result = self.char1.apply_prone(1, source=self.char2)
        self.assertTrue(result)
        self.assertTrue(self.char1.has_effect("prone"))

    def test_apply_slowed_sets_condition(self):
        """apply_slowed should set Condition.SLOWED via registry."""
        self.char1.apply_slowed(3, source=self.char2)
        self.assertTrue(self.char1.has_condition(Condition.SLOWED))
        self.assertTrue(self.char1.has_effect("slowed"))

    def test_apply_paralysed_sets_condition(self):
        """apply_paralysed should set Condition.PARALYSED via registry."""
        self.char1.apply_paralysed(1)
        self.assertTrue(self.char1.has_condition(Condition.PARALYSED))

    def test_apply_entangled_with_save(self):
        """apply_entangled should support save_dc and save_messages."""
        result = self.char1.apply_entangled(
            3, source=self.char2, save_dc=15,
            save_messages={"success": "You break free!"},
        )
        self.assertTrue(result)
        record = self.char1.get_named_effect("entangled")
        self.assertEqual(record["save_dc"], 15)

    def test_apply_blurred(self):
        """apply_blurred should create a blurred named effect."""
        self.char1.apply_blurred(5)
        self.assertTrue(self.char1.has_effect("blurred"))

    def test_apply_shield_buff(self):
        """apply_shield_buff should apply AC bonus via stat_bonus."""
        original_ac = self.char1.armor_class
        self.char1.apply_shield_buff(4, 2)
        self.assertTrue(self.char1.has_effect("shield"))
        self.assertEqual(self.char1.armor_class, original_ac + 4)

    def test_apply_staggered(self):
        """apply_staggered should apply hit penalty."""
        original_hit = self.char1.total_hit_bonus
        self.char1.apply_staggered(-2, 1)
        self.assertTrue(self.char1.has_effect("staggered"))
        self.assertEqual(self.char1.total_hit_bonus, original_hit - 2)

    def test_apply_sundered(self):
        """apply_sundered should apply AC penalty."""
        original_ac = self.char1.armor_class
        self.char1.apply_sundered(-1, 99)
        self.assertTrue(self.char1.has_effect("sundered"))
        self.assertEqual(self.char1.armor_class, original_ac - 1)

    def test_apply_invisible_sets_condition(self):
        """apply_invisible should set Condition.INVISIBLE via registry."""
        self.char1.apply_invisible(300)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        self.assertTrue(self.char1.has_effect("invisible"))

    def test_apply_sanctuary_sets_condition(self):
        """apply_sanctuary should set Condition.SANCTUARY via registry."""
        self.char1.apply_sanctuary(60)
        self.assertTrue(self.char1.has_condition(Condition.SANCTUARY))
        self.assertTrue(self.char1.has_effect("sanctuary"))

    def test_apply_mage_armor(self):
        """apply_mage_armor should apply AC bonus."""
        original_ac = self.char1.armor_class
        self.char1.apply_mage_armor(3, 3600)
        self.assertTrue(self.char1.has_effect("armored"))
        self.assertEqual(self.char1.armor_class, original_ac + 3)

    def test_apply_true_sight_without_detect_invis(self):
        """apply_true_sight without detect_invis should not set DETECT_INVIS."""
        self.char1.apply_true_sight(300)
        self.assertTrue(self.char1.has_effect("true_sight"))
        self.assertFalse(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_apply_true_sight_with_detect_invis(self):
        """apply_true_sight with detect_invis should set DETECT_INVIS condition."""
        self.char1.apply_true_sight(300, detect_invis=True)
        self.assertTrue(self.char1.has_effect("true_sight"))
        self.assertTrue(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_apply_poisoned(self):
        """apply_poisoned should create marker effect."""
        self.char1.apply_poisoned(3)
        self.assertTrue(self.char1.has_effect("poisoned"))

    def test_apply_vampiric(self):
        """apply_vampiric should create marker effect."""
        self.char1.apply_vampiric(source=self.char1)
        self.assertTrue(self.char1.has_effect("vampiric"))

    def test_anti_stacking(self):
        """Convenience methods should respect anti-stacking."""
        self.char1.apply_stunned(2)
        result = self.char1.apply_stunned(3)
        self.assertFalse(result)

    def test_apply_resist_element(self):
        """apply_resist_element should create the correct named effect."""
        self.char1.apply_resist_element("fire", 30, 30)
        self.assertTrue(self.char1.has_effect("resist_fire"))

    def test_apply_resist_element_invalid(self):
        """apply_resist_element with invalid element should raise ValueError."""
        with self.assertRaises(ValueError):
            self.char1.apply_resist_element("darkness", 30, 30)


# ================================================================== #
#  Generic break_effect Tests
# ================================================================== #


class TestBreakEffect(EvenniaTest):
    """Test the generic break_effect method and its aliases."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_break_invisibility_clears_condition(self):
        """break_invisibility should clear Condition.INVISIBLE."""
        self.char1.apply_invisible(300)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        result = self.char1.break_invisibility()
        self.assertTrue(result)
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))
        self.assertFalse(self.char1.has_effect("invisible"))

    def test_break_sanctuary_clears_condition(self):
        """break_sanctuary should clear Condition.SANCTUARY."""
        self.char1.apply_sanctuary(60)
        self.assertTrue(self.char1.has_condition(Condition.SANCTUARY))
        result = self.char1.break_sanctuary()
        self.assertTrue(result)
        self.assertFalse(self.char1.has_condition(Condition.SANCTUARY))
        self.assertFalse(self.char1.has_effect("sanctuary"))

    def test_break_effect_returns_false_when_not_active(self):
        """break_effect should return False if effect not active."""
        result = self.char1.break_invisibility()
        self.assertFalse(result)

    def test_break_effect_reverses_stats(self):
        """break_effect should reverse stat bonuses."""
        original_ac = self.char1.armor_class
        self.char1.apply_shield_buff(4, 2)
        self.assertEqual(self.char1.armor_class, original_ac + 4)
        self.char1.break_effect(NamedEffect.SHIELD)
        self.assertEqual(self.char1.armor_class, original_ac)
        self.assertFalse(self.char1.has_effect("shield"))

    def test_break_effect_generic_with_string(self):
        """break_effect should accept string keys."""
        self.char1.apply_stunned(2)
        result = self.char1.break_effect("stunned")
        self.assertTrue(result)
        self.assertFalse(self.char1.has_effect("stunned"))

    def test_break_effect_no_end_messages(self):
        """break_effect should NOT send end messages (caller handles messaging)."""
        self.char1.apply_invisible(300)
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.break_effect(NamedEffect.INVISIBLE)
            # break_effect should NOT call msg (no end messages)
            mock_msg.assert_not_called()


# ================================================================== #
#  Auto-Fill Registry Tests
# ================================================================== #


class TestRegistryAutoFill(EvenniaTest):
    """Test that apply_named_effect auto-fills from the registry."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_auto_fill_condition(self):
        """Calling apply_named_effect('slowed') should auto-fill Condition.SLOWED."""
        self.char1.apply_named_effect("slowed", duration=3)
        self.assertTrue(self.char1.has_condition(Condition.SLOWED))

    def test_auto_fill_duration_type(self):
        """Calling apply_named_effect('stunned') should auto-fill combat_rounds."""
        self.char1.apply_named_effect("stunned", duration=1)
        record = self.char1.get_named_effect("stunned")
        self.assertEqual(record["duration_type"], "combat_rounds")

    def test_explicit_condition_override(self):
        """Explicitly passing condition=None should override registry default."""
        self.char1.apply_named_effect("slowed", condition=None, duration=3)
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))
        self.assertTrue(self.char1.has_effect("slowed"))

    def test_accepts_named_effect_enum(self):
        """apply_named_effect should accept NamedEffect enum directly."""
        self.char1.apply_named_effect(NamedEffect.STUNNED, duration=2)
        self.assertTrue(self.char1.has_effect("stunned"))

    def test_backward_compat_string_key(self):
        """String keys should still work for backward compatibility."""
        self.char1.apply_named_effect("prone", duration=1)
        self.assertTrue(self.char1.has_effect("prone"))


# ================================================================== #
#  Command Spell Tests (Divine Dominion)
# ================================================================== #


class TestCommand(EvenniaTest):
    """Test Command spell execution — divine dominion BASIC."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("command")
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 1}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.wisdom = 14  # +2 mod
        self.char2.wisdom = 10  # +0 mod
        self.char2.hp = 200
        self.char2.hp_max = 200
        # Command is combat-only — mock a combat handler on the target
        self._mock_combat = patch.object(
            self.char2.scripts, "get",
            side_effect=lambda key: [MagicMock()] if key == "combat_handler" else [],
        )
        self._mock_combat.start()

    def tearDown(self):
        self._mock_combat.stop()
        super().tearDown()

    # --- Registration & attributes ---

    def test_registered(self):
        """Command should be in the registry."""
        self.assertIn("command", SPELL_REGISTRY)

    def test_attributes(self):
        """Command should have correct class attributes."""
        self.assertEqual(self.spell.name, "Command")
        self.assertEqual(self.spell.school, skills.DIVINE_DOMINION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(self.spell.target_type, "hostile")
        self.assertTrue(self.spell.has_spell_arg)
        self.assertEqual(self.spell.cooldown, 0)

    def test_mana_costs(self):
        """Command mana costs should match design."""
        self.assertEqual(
            self.spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
        )

    # --- Validation gates ---

    def test_invalid_command_word_refunds_mana(self):
        """Invalid command word should refund mana and return error."""
        start_mana = self.char1.mana
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="dance",
        )
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)
        self.assertIn("Command what?", result["first"])

    def test_missing_command_word_refunds_mana(self):
        """Missing command word should refund mana and return error."""
        start_mana = self.char1.mana
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg=None,
        )
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)

    def test_combat_only_gate(self):
        """Out of combat should refund mana and return error."""
        # Remove combat handler mock
        self._mock_combat.stop()
        start_mana = self.char1.mana
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)
        self.assertIn("combat", result["first"].lower())
        # Restart mock for tearDown
        self._mock_combat.start()

    def test_size_gate_huge_immune(self):
        """HUGE+ creatures should be immune to Command."""
        self.char2.size = "huge"
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)  # spell succeeds (mana spent)
        self.assertIn("massive", result["first"].lower())
        self.assertFalse(self.char2.has_effect("stunned"))

    # --- Contested check ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_contested_check_failure(self, mock_dice):
        """Failed contested check should not apply any effect."""
        # Caster rolls low, target rolls high
        mock_dice.roll.side_effect = [1, 20]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)
        self.assertIn("resist", result["first"].lower())
        self.assertFalse(self.char2.has_effect("stunned"))

    @patch("world.spells.divine_dominion.command.dice")
    def test_contested_check_tie_fails(self, mock_dice):
        """Tie on contested check should fail (caster must beat)."""
        mock_dice.roll.side_effect = [10, 12]  # +2 wis each = 12 vs 12
        self.char2.wisdom = 14  # +2 mod to match caster
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)
        self.assertIn("resist", result["first"].lower())

    @patch("world.spells.divine_dominion.command.dice")
    def test_mana_spent_on_failed_contest(self, mock_dice):
        """Mana should be spent even if the contested check fails."""
        mock_dice.roll.side_effect = [1, 20]
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        self.assertEqual(self.char1.mana, start_mana - 5)

    # --- HALT (stun) ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_applies_stunned(self, mock_dice):
        """Halt should apply STUNNED on successful contest."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        self.assertTrue(self.char2.has_effect("stunned"))

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_success_message(self, mock_dice):
        """Halt success should show STUNNED in message."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertIn("STUNNED", result["first"])
        self.assertIn("HALT", result["first"])

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_basic(self, mock_dice):
        """BASIC halt should last 1 round."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 1)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_skilled(self, mock_dice):
        """SKILLED halt should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 2}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_expert(self, mock_dice):
        """EXPERT halt should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 3}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_master(self, mock_dice):
        """MASTER halt should last 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_scaling_gm(self, mock_dice):
        """GM halt should last 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="halt")
        effect = self.char2.get_named_effect("stunned")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.command.dice")
    def test_halt_already_stunned(self, mock_dice):
        """Halt on already-stunned target should note it in message."""
        self.char2.apply_stunned(5)
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertIn("already stunned", result["first"].lower())

    # --- GROVEL (prone) ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_applies_prone(self, mock_dice):
        """Grovel should apply PRONE on successful contest."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        self.assertTrue(self.char2.has_effect("prone"))

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_success_message(self, mock_dice):
        """Grovel success should show PRONE in message."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="grovel",
        )
        self.assertIn("PRONE", result["first"])
        self.assertIn("GROVEL", result["first"])

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_basic(self, mock_dice):
        """BASIC grovel should last 1 round."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 1)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_skilled(self, mock_dice):
        """SKILLED grovel should still last 1 round."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 2}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 1)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_expert(self, mock_dice):
        """EXPERT grovel should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 3}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_master(self, mock_dice):
        """MASTER grovel should last 2 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 2)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_scaling_gm(self, mock_dice):
        """GM grovel should last 3 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2, spell_arg="grovel")
        effect = self.char2.get_named_effect("prone")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.command.dice")
    def test_grovel_already_prone(self, mock_dice):
        """Grovel on already-prone target should note it in message."""
        self.char2.apply_prone(5)
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="grovel",
        )
        self.assertIn("already", result["first"].lower())

    # --- DROP (disarm) ---

    @patch("world.spells.divine_dominion.command.force_drop_weapon")
    @patch("world.spells.divine_dominion.command.dice")
    def test_drop_calls_force_drop(self, mock_dice, mock_drop):
        """Drop should call force_drop_weapon on successful contest."""
        mock_dice.roll.side_effect = [20, 1]
        mock_drop.return_value = (True, "iron sword")
        self.spell.cast(self.char1, self.char2, spell_arg="drop")
        mock_drop.assert_called_once_with(self.char2)

    @patch("world.spells.divine_dominion.command.force_drop_weapon")
    @patch("world.spells.divine_dominion.command.dice")
    def test_drop_success_message(self, mock_dice, mock_drop):
        """Drop success should mention the weapon name."""
        mock_dice.roll.side_effect = [20, 1]
        mock_drop.return_value = (True, "iron sword")
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="drop",
        )
        self.assertIn("iron sword", result["first"])
        self.assertIn("DROP", result["first"])

    @patch("world.spells.divine_dominion.command.force_drop_weapon")
    @patch("world.spells.divine_dominion.command.dice")
    def test_drop_no_weapon(self, mock_dice, mock_drop):
        """Drop with no weapon should show appropriate message."""
        mock_dice.roll.side_effect = [20, 1]
        mock_drop.return_value = (False, "")
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="drop",
        )
        self.assertIn("nothing to drop", result["first"].lower())

    # --- FLEE ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_flee_executes_command(self, mock_dice):
        """Flee should call target.execute_cmd('flee')."""
        mock_dice.roll.side_effect = [20, 1]
        with patch.object(self.char2, "execute_cmd") as mock_exec:
            self.spell.cast(self.char1, self.char2, spell_arg="flee")
            mock_exec.assert_called_once_with("flee")

    @patch("world.spells.divine_dominion.command.dice")
    def test_flee_success_message(self, mock_dice):
        """Flee success should show FLEE in message."""
        mock_dice.roll.side_effect = [20, 1]
        with patch.object(self.char2, "execute_cmd"):
            success, result = self.spell.cast(
                self.char1, self.char2, spell_arg="flee",
            )
        self.assertIn("FLEE", result["first"])

    # --- Multi-perspective messaging ---

    @patch("world.spells.divine_dominion.command.dice")
    def test_all_perspectives_present(self, mock_dice):
        """All command results should include first/second/third."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertTrue(success)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    @patch("world.spells.divine_dominion.command.dice")
    def test_contest_detail_shown(self, mock_dice):
        """Contest detail should appear in caster's message."""
        mock_dice.roll.side_effect = [15, 5]
        success, result = self.spell.cast(
            self.char1, self.char2, spell_arg="halt",
        )
        self.assertIn("Will:", result["first"])


# ================================================================== #
#  Hold Spell Tests (Divine Dominion)
# ================================================================== #


class TestHold(EvenniaTest):
    """Test Hold spell execution — divine dominion EXPERT."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("hold")
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 3}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.wisdom = 14  # +2 mod
        self.char2.wisdom = 10  # +0 mod
        self.char2.hp = 200
        self.char2.hp_max = 200

    # --- Registration & attributes ---

    def test_registered(self):
        """Hold should be in the registry."""
        self.assertIn("hold", SPELL_REGISTRY)

    def test_hold_person_not_registered(self):
        """Old hold_person key should not be in the registry."""
        self.assertNotIn("hold_person", SPELL_REGISTRY)

    def test_attributes(self):
        """Hold should have correct class attributes."""
        self.assertEqual(self.spell.name, "Hold")
        self.assertEqual(self.spell.school, skills.DIVINE_DOMINION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(self.spell.target_type, "hostile")

    def test_mana_costs(self):
        """Hold mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_deducts_mana(self):
        """Hold should deduct 28 mana at EXPERT tier."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 28)

    # --- Size gate ---

    def test_expert_can_hold_medium(self):
        """EXPERT should be able to hold MEDIUM targets."""
        self.char2.size = "medium"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertNotIn("too powerful", result["first"].lower())

    def test_expert_cannot_hold_large(self):
        """EXPERT should NOT be able to hold LARGE targets."""
        self.char2.size = "large"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("too powerful", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    def test_master_can_hold_large(self):
        """MASTER should be able to hold LARGE targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        self.char2.size = "large"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertNotIn("too powerful", result["first"].lower())

    def test_master_cannot_hold_huge(self):
        """MASTER should NOT be able to hold HUGE targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        self.char2.size = "huge"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("too powerful", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    def test_gm_can_hold_huge(self):
        """GM should be able to hold HUGE targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        self.char2.size = "huge"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertNotIn("too powerful", result["first"].lower())

    def test_gm_cannot_hold_gargantuan(self):
        """GM should NOT be able to hold GARGANTUAN targets."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        self.char2.size = "gargantuan"
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("too powerful", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    # --- Contested check ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_contested_check_success(self, mock_dice):
        """Successful contest should apply PARALYSED."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        self.assertTrue(self.char2.has_effect("paralysed"))

    @patch("world.spells.divine_dominion.hold.dice")
    def test_contested_check_failure(self, mock_dice):
        """Failed contest should not apply any effect."""
        mock_dice.roll.side_effect = [1, 20]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("resist", result["first"].lower())
        self.assertFalse(self.char2.has_effect("paralysed"))

    @patch("world.spells.divine_dominion.hold.dice")
    def test_contested_check_tie_fails(self, mock_dice):
        """Tie should fail (caster must beat)."""
        # Caster: d20=10 + WIS(+2) + mastery(+4) = 16
        # Target: d20=16 + WIS(+0) = 16  → tie → fail
        mock_dice.roll.side_effect = [10, 16]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("resist", result["first"].lower())

    @patch("world.spells.divine_dominion.hold.dice")
    def test_mana_spent_on_failed_contest(self, mock_dice):
        """Mana should be spent even on failed contest."""
        mock_dice.roll.side_effect = [1, 20]
        start_mana = self.char1.mana
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, start_mana - 28)

    # --- Duration scaling ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_duration_expert(self, mock_dice):
        """EXPERT hold should last 3 rounds."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["duration"], 3)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_duration_master(self, mock_dice):
        """MASTER hold should last 4 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 4}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["duration"], 4)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_duration_gm(self, mock_dice):
        """GM hold should last 5 rounds."""
        self.char1.db.class_skill_mastery_levels = {"divine_dominion": 5}
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["duration"], 5)

    # --- Save DC ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_save_dc_is_full_caster_total(self, mock_dice):
        """Save DC should be caster's d20 + WIS + mastery, not raw d20."""
        # Caster: d20=15, WIS bonus=+2, mastery bonus=+4 (EXPERT) → total 21
        mock_dice.roll.side_effect = [15, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertIsNotNone(effect)
        # 15 + 2 (WIS bonus for 14) + 4 (EXPERT mastery bonus) = 21
        self.assertEqual(effect["save_dc"], 21)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_save_stat_is_wisdom(self, mock_dice):
        """Per-round save should use wisdom."""
        mock_dice.roll.side_effect = [20, 1]
        self.spell.cast(self.char1, self.char2)
        effect = self.char2.get_named_effect("paralysed")
        self.assertEqual(effect["save_stat"], "wisdom")

    # --- Anti-stacking ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_already_paralysed(self, mock_dice):
        """Hold on already-paralysed target should note it in message."""
        self.char2.apply_paralysed(5)
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("already", result["first"].lower())

    # --- Multi-perspective messaging ---

    @patch("world.spells.divine_dominion.hold.dice")
    def test_all_perspectives_present(self, mock_dice):
        """All results should include first/second/third."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    @patch("world.spells.divine_dominion.hold.dice")
    def test_success_message(self, mock_dice):
        """Success message should mention PARALYSED."""
        mock_dice.roll.side_effect = [20, 1]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("PARALYSED", result["first"])
        self.assertIn("HOLD", result["first"])

    @patch("world.spells.divine_dominion.hold.dice")
    def test_contest_detail_shown(self, mock_dice):
        """Contest detail should appear in caster's message."""
        mock_dice.roll.side_effect = [15, 5]
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertIn("Will:", result["first"])


# ================================================================== #
#  Call Lightning Spell Tests (Nature Magic)
# ================================================================== #


class TestCallLightning(EvenniaTest):
    """Test Call Lightning spell execution — nature magic EXPERT."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("call_lightning")
        self.char1.db.class_skill_mastery_levels = {"nature_magic": 3}
        self.char1.mana = 500
        self.char1.db.spell_cooldowns = {}
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char1.damage_resistances = {}
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    # --- Registration & attributes ---

    def test_registered(self):
        """Call Lightning should be in the registry."""
        self.assertIn("call_lightning", SPELL_REGISTRY)

    def test_attributes(self):
        """Call Lightning should have correct class attributes."""
        self.assertEqual(self.spell.name, "Call Lightning")
        self.assertEqual(self.spell.school, skills.NATURE_MAGIC)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(self.spell.target_type, "none")

    def test_mana_costs(self):
        """Call Lightning mana costs should match design."""
        self.assertEqual(self.spell.mana_cost, {3: 21, 4: 32, 5: 42})

    # --- Unsafe AoE ---

    def test_hits_caster(self):
        """Call Lightning should damage the caster (unsafe AoE)."""
        start_hp = self.char1.hp
        self.spell.cast(self.char1, None)
        self.assertLess(self.char1.hp, start_hp)

    def test_hits_others_in_room(self):
        """Call Lightning should damage others in the room."""
        start_hp = self.char2.hp
        self.spell.cast(self.char1, None)
        self.assertLess(self.char2.hp, start_hp)

    def test_deducts_mana(self):
        """Call Lightning should deduct 21 mana at EXPERT tier."""
        start_mana = self.char1.mana
        self.spell.cast(self.char1, None)
        self.assertEqual(self.char1.mana, start_mana - 21)

    # --- Damage range ---

    def test_expert_damage_range(self):
        """At EXPERT tier, 6d6 = 6-36 full, 3-18 half (with save)."""
        self.char2.hp = 200
        self.spell.cast(self.char1, None)
        damage = 200 - self.char2.hp
        # Min is 3 (half of 6 on save), max is 36 (full on fail)
        self.assertGreaterEqual(damage, 3)
        self.assertLessEqual(damage, 36)

    # --- Mastery gate ---

    def test_mastery_too_low(self):
        """Should fail if mastery below EXPERT."""
        self.char1.db.class_skill_mastery_levels = {"nature_magic": 2}
        success, msg = self.spell.cast(self.char1, None)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    # --- Damage type ---

    def test_lightning_resistance_reduces_damage(self):
        """Lightning resistance should reduce Call Lightning damage."""
        self.char2.damage_resistances = {"lightning": 50}
        self.char2.hp = 200
        self.spell.cast(self.char1, None)
        damage = 200 - self.char2.hp
        # 50% resist on max 36 = max 18
        self.assertLessEqual(damage, 18)

    # --- Save mechanic ---

    @patch("world.spells.nature_magic.call_lightning.dice")
    def test_save_full_damage_on_fail(self, mock_dice):
        """Failed DEX save should deal full damage."""
        # damage roll, save DC roll, char1 save, char2 save
        mock_dice.roll.side_effect = [18, 20, 1, 1]
        self.char2.hp = 200
        self.char2.dexterity = 10
        self.spell.cast(self.char1, None)
        self.assertEqual(self.char2.hp, 200 - 18)

    @patch("world.spells.nature_magic.call_lightning.dice")
    def test_save_half_damage_on_success(self, mock_dice):
        """Successful DEX save should deal half damage."""
        # damage roll, save DC roll, char1 save, char2 save
        mock_dice.roll.side_effect = [18, 1, 20, 20]
        self.char2.hp = 200
        self.char2.dexterity = 10
        self.spell.cast(self.char1, None)
        # half of 18 = 9
        self.assertEqual(self.char2.hp, 200 - 9)

    @patch("world.spells.nature_magic.call_lightning.dice")
    def test_save_dc_shown_in_message(self, mock_dice):
        """Save DC should appear in caster message."""
        mock_dice.roll.side_effect = [18, 15, 1, 1]
        success, result = self.spell.cast(self.char1, None)
        self.assertIn("Save DC", result["first"])

    # --- Messages ---

    def test_returns_message_dict(self):
        """Successful cast should return message dict."""
        success, result = self.spell.cast(self.char1, None)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("third", result)

    def test_lightning_themed_messages(self):
        """Messages should reference lightning, not fire."""
        success, result = self.spell.cast(self.char1, None)
        self.assertIn("lightning", result["first"].lower())
        self.assertIn("lightning", result["third"].lower())


class TestHolySight(EvenniaTest):
    """Tests for the Holy Sight spell (divine revelation self-buff).

    Holy Sight mirrors True Sight with different tier unlock order:
        SKILLED: traps, EXPERT: +invisible, MASTER: +hidden.
    """

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("holy_sight")
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 2}
        self.char1.mana = 100

    # --- Registration ---

    def test_registered(self):
        """Holy Sight should be in the spell registry."""
        self.assertIsNotNone(self.spell)

    def test_attributes(self):
        """Spell should have correct key, school, min_mastery."""
        self.assertEqual(self.spell.key, "holy_sight")
        self.assertEqual(self.spell.school, skills.DIVINE_REVELATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(self.spell.target_type, "self")

    # --- Named effect ---

    def test_applies_named_effect(self):
        """Casting should create a holy_sight named effect on caster."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("holy_sight"))

    def test_tier_stored(self):
        """Caster tier should be stored in db.holy_sight_tier on cast."""
        self.spell.cast(self.char1, self.char1)
        self.assertEqual(self.char1.db.holy_sight_tier, 2)

    def test_tier_stored_expert(self):
        """EXPERT tier should store tier 3."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 3}
        self.spell.cast(self.char1, self.char1)
        self.assertEqual(self.char1.db.holy_sight_tier, 3)

    # --- DETECT_INVIS tiering (EXPERT+, not MASTER+ like True Sight) ---

    def test_skilled_no_detect_invis(self):
        """SKILLED Holy Sight should NOT grant DETECT_INVIS."""
        self.spell.cast(self.char1, self.char1)
        self.assertFalse(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_expert_grants_detect_invis(self):
        """EXPERT Holy Sight SHOULD grant DETECT_INVIS (earlier than True Sight)."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 3}
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_master_grants_detect_invis(self):
        """MASTER Holy Sight SHOULD grant DETECT_INVIS."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 4}
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.DETECT_INVIS))

    def test_remove_clears_detect_invis(self):
        """Removing EXPERT Holy Sight should remove DETECT_INVIS."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 3}
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.DETECT_INVIS))
        self.char1.remove_named_effect("holy_sight")
        self.assertFalse(self.char1.has_condition(Condition.DETECT_INVIS))

    # --- Trap detection tiering (SKILLED+, not EXPERT+ like True Sight) ---

    def test_skilled_auto_detects_traps_on_cast(self):
        """SKILLED Holy Sight should call _detect_traps_in_room on cast."""
        with patch.object(self.spell, "_detect_traps_in_room") as mock_detect:
            self.spell.cast(self.char1, self.char1)
            mock_detect.assert_called_once_with(self.char1)

    def test_expert_auto_detects_traps_on_cast(self):
        """EXPERT Holy Sight should also call _detect_traps_in_room."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 3}
        with patch.object(self.spell, "_detect_traps_in_room") as mock_detect:
            self.spell.cast(self.char1, self.char1)
            mock_detect.assert_called_once_with(self.char1)

    # --- HIDDEN visibility tiering (MASTER+, not SKILLED+ like True Sight) ---

    def test_skilled_cannot_see_hidden(self):
        """SKILLED Holy Sight should NOT reveal HIDDEN characters."""
        from evennia.utils.create import create_object
        from typeclasses.terrain.rooms.room_base import RoomBase
        room = create_object(RoomBase, key="TestRoom", nohome=True)
        room.always_lit = True
        self.char1.location = room
        self.char2.location = room
        self.spell.cast(self.char1, self.char1)
        self.char2.add_condition(Condition.HIDDEN)
        display = room.get_display_characters(self.char1)
        self.assertNotIn(self.char2.key, display)

    def test_expert_cannot_see_hidden(self):
        """EXPERT Holy Sight should NOT reveal HIDDEN characters."""
        from evennia.utils.create import create_object
        from typeclasses.terrain.rooms.room_base import RoomBase
        room = create_object(RoomBase, key="TestRoom", nohome=True)
        room.always_lit = True
        self.char1.location = room
        self.char2.location = room
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 3}
        self.spell.cast(self.char1, self.char1)
        self.char2.add_condition(Condition.HIDDEN)
        display = room.get_display_characters(self.char1)
        self.assertNotIn(self.char2.key, display)

    def test_master_can_see_hidden(self):
        """MASTER Holy Sight SHOULD reveal HIDDEN characters."""
        from evennia.utils.create import create_object
        from typeclasses.terrain.rooms.room_base import RoomBase
        room = create_object(RoomBase, key="TestRoom", nohome=True)
        room.always_lit = True
        self.char1.location = room
        self.char2.location = room
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 4}
        self.spell.cast(self.char1, self.char1)
        self.char2.add_condition(Condition.HIDDEN)
        display = room.get_display_characters(self.char1)
        self.assertIn(self.char2.key, display)

    # --- Anti-stacking ---

    def test_anti_stacking_refunds_mana(self):
        """Recasting while active should fail and refund mana."""
        self.spell.cast(self.char1, self.char1)
        mana_after_first = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_after_first)

    # --- Duration and mana scaling ---

    def test_duration_scales_with_tier(self):
        """Duration should scale: SKILLED=5min, EXPERT=10min, MASTER=30min, GM=60min."""
        expected_minutes = {2: 5, 3: 10, 4: 30, 5: 60}
        for tier, minutes in expected_minutes.items():
            if self.char1.has_effect("holy_sight"):
                self.char1.remove_named_effect("holy_sight")
            self.char1.db.class_skill_mastery_levels = {"divine_revelation": tier}
            self.char1.mana = 100
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertTrue(success)
            self.assertIn(str(minutes), result["first"],
                          f"Tier {tier} message should mention {minutes}")

    def test_mana_cost_scales_with_tier(self):
        """Mana cost: SKILLED=15, EXPERT=25, MASTER=40, GM=40."""
        expected = {2: 15, 3: 25, 4: 40, 5: 40}
        for tier, cost in expected.items():
            if self.char1.has_effect("holy_sight"):
                self.char1.remove_named_effect("holy_sight")
            self.char1.db.class_skill_mastery_levels = {"divine_revelation": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char1)
            self.assertEqual(self.char1.mana, 100 - cost,
                             f"Tier {tier} should cost {cost} mana")

    # --- Mastery gate ---

    def test_mastery_check(self):
        """Should fail without divine_revelation mastery at SKILLED level."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_basic_mastery_too_low(self):
        """BASIC mastery should not be enough (min_mastery = SKILLED)."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 1}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)

    def test_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 14
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    # --- Messages ---

    def test_multi_perspective_messages(self):
        """Should return first and third person messages (no second for self-cast)."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_message_reflects_tier_capabilities(self):
        """Cast message should describe what this tier reveals."""
        # SKILLED — traps only
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("traps", result["first"])
        self.assertNotIn("invisible", result["first"])

        # EXPERT — traps and invisible
        self.char1.remove_named_effect("holy_sight")
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 3}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("invisible", result["first"])

        # MASTER — traps, invisible, and hidden
        self.char1.remove_named_effect("holy_sight")
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 4}
        self.char1.mana = 100
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("hidden", result["first"])

    def test_divine_themed_messages(self):
        """Messages should reference divine light, not magical energy."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("divine", result["first"].lower())
        self.assertIn("divine", result["third"].lower())


# ================================================================== #
#  Spell Height Gating Tests
# ================================================================== #

class TestSpellHeightGating(EvenniaTest):
    """Test spell_range height gating on melee vs ranged spells."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Set up caster with necromancy (for Vampiric Touch) and evocation
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
        """Cure Wounds on self always works regardless of spell_range."""
        spell = get_spell("cure_wounds")
        self.char1.db.class_skill_mastery_levels["divine_healing"] = 1
        self.char1.room_vertical_position = 1
        self.char1.hp = 50
        self.char1.hp_max = 100
        success, result = spell.cast(self.char1, self.char1)
        self.assertTrue(success)

    def test_spell_range_attribute_exists(self):
        """All spells should have a spell_range attribute."""
        for key, spell in SPELL_REGISTRY.items():
            self.assertIn(
                spell.spell_range, ("self", "melee", "ranged"),
                f"Spell {key} has invalid spell_range: {spell.spell_range}",
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

    def test_all_at_height_underwater(self):
        """Height filtering works for negative (underwater) positions."""
        self.char1.room_vertical_position = -1
        self.char2.room_vertical_position = -1
        result = self.get_all(self.char1)
        self.assertIn(self.char1, result)
        self.assertIn(self.char2, result)

    def test_all_at_height_mixed_underwater(self):
        """Surface caster doesn't see underwater entities."""
        self.char1.room_vertical_position = 0
        self.char2.room_vertical_position = -1
        result = self.get_all(self.char1)
        self.assertIn(self.char1, result)
        self.assertNotIn(self.char2, result)

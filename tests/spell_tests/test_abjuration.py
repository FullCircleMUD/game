"""
Tests for the abjuration spell school.

Tests:
    - Registry: all abjuration spells registered with correct attributes
    - Mage Armor: AC buff via named effect, scaling, anti-stacking
    - Resist: element resistance buff, spell_arg parsing, anti-stacking
    - School membership: get_spells_for_school returns expected set
    - Descriptions and mechanics: all spells have documentation

evennia test --settings settings tests.spell_tests.test_abjuration
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import get_spell, get_spells_for_school


# ================================================================== #
#  Abjuration Registry Tests
# ================================================================== #

class TestAbjurationRegistry(EvenniaTest):
    """Test all abjuration spells are registered correctly."""

    def create_script(self):
        pass

    def test_shield_registered(self):
        spell = get_spell("shield")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ABJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "self")

    def test_mage_armor_registered(self):
        spell = get_spell("mage_armor")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ABJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "self")
        self.assertEqual(spell.mana_cost, {1: 3, 2: 5, 3: 7, 4: 9, 5: 12})

    def test_resist_registered(self):
        spell = get_spell("resist")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ABJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "friendly")
        self.assertTrue(spell.has_spell_arg)

    def test_antimagic_field_registered(self):
        spell = get_spell("antimagic_field")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ABJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_group_resist_registered(self):
        spell = get_spell("group_resist")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ABJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.MASTER)
        self.assertEqual(spell.mana_cost, {4: 56, 5: 64})

    def test_invulnerability_registered(self):
        spell = get_spell("invulnerability")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ABJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(spell.mana_cost, {5: 100})

    def test_abjuration_school_has_all_spells(self):
        abj = get_spells_for_school("abjuration")
        expected = {
            "shield", "mage_armor", "resist", "shadowcloak",
            "antimagic_field", "group_resist", "invulnerability",
            "feather_fall",
        }
        self.assertEqual(set(abj.keys()), expected)

    def test_abjuration_description_and_mechanics(self):
        """All abjuration spells should have description and mechanics."""
        for key in ["shield", "mage_armor", "resist", "shadowcloak",
                     "antimagic_field", "group_resist", "invulnerability"]:
            spell = get_spell(key)
            self.assertTrue(spell.description, f"{key} missing description")
            self.assertTrue(spell.mechanics, f"{key} missing mechanics")


# ================================================================== #
#  Mage Armor Execution Tests
# ================================================================== #

class TestMageArmor(EvenniaTest):
    """Test Mage Armor spell execution — AC buff via named effect system."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("mage_armor")
        self.char1.db.class_skill_mastery_levels = {"abjuration": 1}
        self.char1.base_mana_max = 200
        self.char1.mana_max = 200
        self.char1.mana = 100

    def test_mage_armor_applies_named_effect(self):
        """Casting should create a armored named effect."""
        success, result = self.spell.cast(self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("armored"))

    def test_mage_armor_ac_bonus_scaling(self):
        """AC bonus should scale: +3/+3/+4/+4/+5 across tiers."""
        expected_ac = {1: 3, 2: 3, 3: 4, 4: 4, 5: 5}
        for tier, ac in expected_ac.items():
            self.assertEqual(self.spell._SCALING[tier][0], ac)

    def test_mage_armor_duration_scaling(self):
        """Duration should scale: 1/2/2/3/3 hours across tiers."""
        expected_hours = {1: 1, 2: 2, 3: 2, 4: 3, 5: 3}
        for tier, hours in expected_hours.items():
            self.assertEqual(self.spell._SCALING[tier][1], hours)

    def test_mage_armor_message_includes_ac_and_duration(self):
        """Cast message should include AC bonus and duration."""
        success, result = self.spell.cast(self.char1)
        self.assertTrue(success)
        self.assertIn("+3 AC", result["first"])
        self.assertIn("1 hour", result["first"])

    def test_mage_armor_anti_stacking(self):
        """Should refuse to recast while already active."""
        success1, _ = self.spell.cast(self.char1)
        self.assertTrue(success1)
        mana_after_first = self.char1.mana
        success2, result = self.spell.cast(self.char1)
        self.assertFalse(success2)
        self.assertIn("already active", result["first"].lower())
        # Should not deduct mana on failed recast
        self.assertEqual(self.char1.mana, mana_after_first)

    def test_mage_armor_deducts_mana(self):
        """Should deduct 3 mana at tier 1."""
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.mana, 97)

    def test_mage_armor_deducts_mana_tier5(self):
        """Should deduct 12 mana at GM tier."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 5}
        self.spell.cast(self.char1)
        self.assertEqual(self.char1.mana, 88)

    def test_mage_armor_mastery_check(self):
        """Should fail without abjuration mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_mage_armor_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 2
        success, msg = self.spell.cast(self.char1)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_mage_armor_multi_perspective_messages(self):
        """Should return first and third person messages."""
        success, result = self.spell.cast(self.char1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])  # self-targeted
        self.assertIn("third", result)

    def test_mage_armor_removable(self):
        """Should be removable via remove_named_effect (dispel pattern)."""
        self.spell.cast(self.char1)
        self.assertTrue(self.char1.has_effect("armored"))
        self.char1.remove_named_effect("armored")
        self.assertFalse(self.char1.has_effect("armored"))

    def test_mage_armor_scaling_table(self):
        """Verify full scaling table: (AC, hours) per tier."""
        expected = {
            1: (3, 1),
            2: (3, 2),
            3: (4, 2),
            4: (4, 3),
            5: (5, 3),
        }
        self.assertEqual(self.spell._SCALING, expected)


# ================================================================== #
#  Resist Execution Tests
# ================================================================== #

class TestResist(EvenniaTest):
    """Test Resist spell — element resistance via named effect system."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("resist")
        self.char1.db.class_skill_mastery_levels = {"abjuration": 2}
        self.char1.base_mana_max = 500
        self.char1.mana_max = 500
        self.char1.mana = 100
        self.char1.db.spell_cooldowns = {}
        self.char2.hp = 200
        self.char2.hp_max = 200
        self.char2.damage_resistances = {}

    def test_registered(self):
        """Resist should be in the registry."""
        self.assertIsNotNone(self.spell)
        self.assertEqual(self.spell.key, "resist")

    def test_attributes(self):
        """Resist should have correct class attributes."""
        self.assertEqual(self.spell.school, skills.ABJURATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(self.spell.target_type, "friendly")
        self.assertTrue(self.spell.has_spell_arg)
        self.assertEqual(self.spell.cooldown, 0)

    def test_missing_element_refunds_mana(self):
        """Should fail and refund mana when no element specified."""
        start_mana = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1, spell_arg=None)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)
        self.assertIn("resist what", result["first"].lower())

    def test_invalid_element_refunds_mana(self):
        """Should fail and refund mana for invalid element."""
        start_mana = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1, spell_arg="magic")
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, start_mana)

    def test_applies_fire_resistance(self):
        """Should grant 20% fire resistance at tier 2."""
        success, result = self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("resist_fire"))
        self.assertEqual(self.char1.get_resistance("fire"), 20)

    def test_applies_cold_resistance(self):
        """Should grant cold resistance."""
        success, result = self.spell.cast(self.char1, self.char1, spell_arg="cold")
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("resist_cold"))
        self.assertEqual(self.char1.get_resistance("cold"), 20)

    def test_resistance_scales_with_tier(self):
        """Tier 5 should grant 60% resistance."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 5}
        success, result = self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.assertTrue(success)
        self.assertEqual(self.char1.get_resistance("fire"), 60)

    def test_anti_stacking_refunds_mana(self):
        """Should refuse and refund mana if same element already active."""
        self.spell.cast(self.char1, self.char1, spell_arg="fire")
        mana_after_first = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_after_first)
        self.assertIn("already", result["first"].lower())

    def test_different_elements_stack(self):
        """Should allow fire + cold resistance simultaneously."""
        self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.spell.cast(self.char1, self.char1, spell_arg="cold")
        self.assertTrue(self.char1.has_effect("resist_fire"))
        self.assertTrue(self.char1.has_effect("resist_cold"))
        self.assertEqual(self.char1.get_resistance("fire"), 20)
        self.assertEqual(self.char1.get_resistance("cold"), 20)

    def test_cast_on_target(self):
        """Should apply resistance to a friendly target."""
        self.char2.damage_resistances = {}
        success, result = self.spell.cast(self.char1, self.char2, spell_arg="fire")
        self.assertTrue(success)
        self.assertTrue(self.char2.has_effect("resist_fire"))
        self.assertEqual(self.char2.get_resistance("fire"), 20)

    def test_cast_defaults_to_self(self):
        """When target is caster, should apply to self."""
        success, result = self.spell.cast(self.char1, self.char1, spell_arg="acid")
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("resist_acid"))

    def test_mastery_check(self):
        """BASIC mastery should not be able to cast Resist."""
        self.char1.db.class_skill_mastery_levels = {"abjuration": 1}
        success, msg = self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.assertFalse(success)

    def test_multi_perspective_messages(self):
        """Cast should return first/second/third person messages."""
        success, result = self.spell.cast(self.char1, self.char2, spell_arg="fire")
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)
        self.assertIsNotNone(result["second"])

    def test_self_cast_no_second_message(self):
        """Self-cast should have no second person message."""
        success, result = self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.assertTrue(success)
        self.assertIsNone(result["second"])

    def test_deducts_mana(self):
        """Should deduct 8 mana at tier 2."""
        self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.assertEqual(self.char1.mana, 92)

    def test_removal_clears_resistance(self):
        """Removing the effect should reverse the resistance bonus."""
        self.spell.cast(self.char1, self.char1, spell_arg="fire")
        self.assertEqual(self.char1.get_resistance("fire"), 20)
        self.char1.remove_named_effect("resist_fire")
        self.assertEqual(self.char1.get_resistance("fire"), 0)
        self.assertFalse(self.char1.has_effect("resist_fire"))

    def test_all_valid_elements(self):
        """All five valid elements should work."""
        self.char1.mana = 500
        for element in ["fire", "cold", "lightning", "acid", "poison"]:
            success, _ = self.spell.cast(self.char1, self.char1, spell_arg=element)
            self.assertTrue(success, f"Failed to cast resist {element}")
            self.assertTrue(
                self.char1.has_effect(f"resist_{element}"),
                f"Missing effect resist_{element}",
            )

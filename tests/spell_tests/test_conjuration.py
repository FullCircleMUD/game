"""
Tests for the conjuration spell school.

Tests:
    - Registry: all conjuration spells registered with correct attributes
    - Acid Arrow: DoT application, scaling, anti-stacking, script lifecycle
    - School membership: get_spells_for_school returns expected set
    - Descriptions and mechanics: all spells have documentation

evennia test --settings settings tests.spell_tests.test_conjuration
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import get_spell, get_spells_for_school


# ================================================================== #
#  Conjuration Registry Tests
# ================================================================== #

class TestConjurationRegistry(EvenniaTest):
    """Test all conjuration spells are registered correctly."""

    def create_script(self):
        pass

    def test_acid_arrow_registered(self):
        spell = get_spell("acid_arrow")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "actor_hostile")
        self.assertEqual(spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_teleport_registered(self):
        spell = get_spell("teleport")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {2: 15, 3: 25, 4: 40, 5: 40})

    def test_dimensional_lock_registered(self):
        spell = get_spell("dimensional_lock")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_conjure_elemental_registered(self):
        spell = get_spell("conjure_elemental")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.MASTER)
        self.assertEqual(spell.mana_cost, {4: 56, 5: 64})

    def test_gate_registered(self):
        spell = get_spell("gate")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.CONJURATION)
        self.assertEqual(spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(spell.mana_cost, {5: 100})
        self.assertEqual(spell.target_type, "none")

    def test_conjuration_school_has_all_spells(self):
        conj = get_spells_for_school("conjuration")
        expected = {
            "acid_arrow", "teleport", "dimensional_lock",
            "conjure_elemental", "gate",
            "light_spell", "find_familiar",
            "create_water", "knock",
        }
        self.assertEqual(set(conj.keys()), expected)

    def test_conjuration_description_and_mechanics(self):
        """All conjuration spells should have description and mechanics."""
        for key in ["acid_arrow", "teleport", "dimensional_lock",
                     "conjure_elemental", "gate"]:
            spell = get_spell(key)
            self.assertTrue(spell.description, f"{key} missing description")
            self.assertTrue(spell.mechanics, f"{key} missing mechanics")


# ================================================================== #
#  Acid Arrow Execution Tests
# ================================================================== #

class TestAcidArrow(EvenniaTest):
    """Test Acid Arrow spell execution — DoT via AcidDoTScript."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("acid_arrow")
        self.char1.db.class_skill_mastery_levels = {"conjuration": 1}
        self.char1.mana = 100
        self.char2.hp = 100
        self.char2.hp_max = 100
        self.char2.damage_resistances = {}

    def test_acid_arrow_applies_named_effect(self):
        """Casting should create an acid_arrow named effect on target."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertTrue(self.char2.has_effect("acid_arrow"))

    def test_acid_arrow_creates_dot_script(self):
        """Casting should attach an AcidDoTScript to the target."""
        self.spell.cast(self.char1, self.char2)
        scripts = self.char2.scripts.get("acid_dot")
        self.assertTrue(scripts)
        self.assertEqual(scripts[0].db.remaining_ticks, 1)  # tier 1

    def test_acid_arrow_dot_rounds_scale_with_tier(self):
        """DoT rounds should equal mastery tier."""
        for tier in range(1, 6):
            # Clean up from previous iteration
            if self.char2.has_effect("acid_arrow"):
                self.char2.remove_named_effect("acid_arrow")
            existing = self.char2.scripts.get("acid_dot")
            if existing:
                existing[0].delete()

            self.char1.db.class_skill_mastery_levels = {"conjuration": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char2)
            scripts = self.char2.scripts.get("acid_dot")
            self.assertEqual(
                scripts[0].db.remaining_ticks, tier,
                f"Tier {tier} should have {tier} rounds"
            )

    def test_acid_arrow_dot_tick_deals_damage(self):
        """Each tick should deal 1d4+1 acid damage."""
        self.spell.cast(self.char1, self.char2)
        scripts = self.char2.scripts.get("acid_dot")
        hp_before = self.char2.hp
        with patch("typeclasses.scripts.acid_dot_script.dice") as mock_dice:
            mock_dice.roll.return_value = 4  # 1d4+1 = 4
            scripts[0].tick_acid()
            mock_dice.roll.assert_called_with("1d4+1")
        self.assertLess(self.char2.hp, hp_before)

    def test_acid_arrow_dot_expires_after_ticks(self):
        """DoT script should remove named effect after all ticks."""
        self.spell.cast(self.char1, self.char2)
        scripts = self.char2.scripts.get("acid_dot")
        # Tier 1 = 1 tick. After ticking once, should expire.
        with patch("typeclasses.scripts.acid_dot_script.dice") as mock_dice:
            mock_dice.roll.return_value = 3
            scripts[0].tick_acid()
        self.assertFalse(self.char2.has_effect("acid_arrow"))

    def test_acid_arrow_anti_stacking_replaces(self):
        """New cast should replace existing acid arrow, not stack."""
        self.char1.db.class_skill_mastery_levels = {"conjuration": 3}
        self.spell.cast(self.char1, self.char2)
        scripts1 = self.char2.scripts.get("acid_dot")
        self.assertEqual(scripts1[0].db.remaining_ticks, 3)

        # Recast — should replace with fresh 3-round DoT
        self.spell.cast(self.char1, self.char2)
        scripts2 = self.char2.scripts.get("acid_dot")
        self.assertEqual(len(scripts2), 1)  # only one script
        self.assertEqual(scripts2[0].db.remaining_ticks, 3)

    def test_acid_arrow_deducts_mana(self):
        """Should deduct 5 mana at tier 1."""
        self.spell.cast(self.char1, self.char2)
        self.assertEqual(self.char1.mana, 95)

    def test_acid_arrow_mastery_check(self):
        """Should fail without conjuration mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_acid_arrow_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 4
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_acid_arrow_multi_perspective_messages(self):
        """Should return first, second, and third person messages."""
        success, result = self.spell.cast(self.char1, self.char2)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIn("second", result)
        self.assertIn("third", result)

    def test_acid_arrow_same_mana_as_magic_missile(self):
        """Mana costs should match Magic Missile exactly."""
        mm = get_spell("magic_missile")
        self.assertEqual(self.spell.mana_cost, mm.mana_cost)

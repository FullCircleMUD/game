"""
Tests for the nature magic spell school.

Tests:
    - Entangle: root effect via contested roll, duration scaling, messages
    - Call Lightning: unsafe AoE, save mechanic, lightning damage type

evennia test --settings settings tests.spell_tests.test_nature_magic
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import SPELL_REGISTRY, get_spell


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
        self.assertEqual(self.spell.target_type, "actor_hostile")

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

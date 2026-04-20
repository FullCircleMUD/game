"""
Divine Judgement spell tests.

    evennia test --settings settings tests.spell_tests.test_divine_judgement
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import SPELL_REGISTRY, get_spell


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

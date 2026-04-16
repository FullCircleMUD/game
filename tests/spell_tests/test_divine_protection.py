"""
Divine Protection spell tests.

    evennia test --settings settings tests.spell_tests.test_divine_protection
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import SPELL_REGISTRY, get_spell


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

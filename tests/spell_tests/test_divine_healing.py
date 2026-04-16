"""
Divine Healing spell tests.

    evennia test --settings settings tests.spell_tests.test_divine_healing
"""

from evennia.utils.test_resources import EvenniaTest

from world.spells.registry import get_spell


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

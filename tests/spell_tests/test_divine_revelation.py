"""
Tests for the divine revelation spell school.

Tests:
    - Holy Insight: divine sight, alignment/evil/undead detection, actor identification
    - Holy Sight: self-buff (Divine Revelation flavour of True Sight)

evennia test --settings settings tests.spell_tests.test_divine_revelation
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import SPELL_REGISTRY, get_spell


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
        self.assertEqual(self.spell.target_type, "items_inventory_then_room_all")

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

    # NOTE: Actor tests (divine sight, alignment, evil/undead detection)
    # removed — Holy Insight is now items-only (inspect_item). Those
    # tests belong on TestDivineScrutiny which handles actor identification
    # with the divine sight overlay.

    def test_mastery_too_low(self):
        """Should fail if mastery is 0."""
        self.char1.db.class_skill_mastery_levels = {"divine_revelation": 0}
        success, msg = self.spell.cast(self.char1, self.char2)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())


class TestHolySight(EvenniaTest):
    """Tests for Holy Sight — Divine Revelation flavour of True Sight.

    Holy Sight is a thin subclass of TrueSight: same capability (see HIDDEN),
    same mana cost, same duration scaling, same `true_sight` named effect.
    Only school, name, and flavour wording differ.
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
        self.assertIn("holy_sight", SPELL_REGISTRY)
        self.assertIsNotNone(self.spell)

    def test_attributes(self):
        """Spell should have correct key, school, min_mastery, target."""
        self.assertEqual(self.spell.key, "holy_sight")
        self.assertEqual(self.spell.name, "Holy Sight")
        self.assertEqual(self.spell.school, skills.DIVINE_REVELATION)
        self.assertEqual(self.spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(self.spell.target_type, "self")

    # --- Named effect (shared with True Sight) ---

    def test_applies_true_sight_effect(self):
        """Casting should apply the shared `true_sight` named effect."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("true_sight"))

    def test_no_detect_invis_at_any_tier(self):
        """Holy Sight should NOT grant DETECT_INVIS at any tier (parity with True Sight)."""
        for tier in (2, 3, 4, 5):
            if self.char1.has_effect("true_sight"):
                self.char1.remove_named_effect("true_sight")
            self.char1.db.class_skill_mastery_levels = {"divine_revelation": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char1)
            self.assertFalse(
                self.char1.has_condition(Condition.DETECT_INVIS),
                f"Tier {tier} should NOT grant DETECT_INVIS",
            )

    # --- Anti-stacking (shared `true_sight` effect, so cross-school anti-stacks too) ---

    def test_anti_stacking_refunds_mana(self):
        """Recasting while active should fail and refund mana."""
        self.spell.cast(self.char1, self.char1)
        mana_after_first = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_after_first)

    # --- Duration and mana scaling (matches True Sight) ---

    def test_duration_scales_with_tier(self):
        """Duration should scale: SKILLED=30, EXPERT=60, MASTER=90, GM=120."""
        expected_minutes = {2: 30, 3: 60, 4: 90, 5: 120}
        for tier, minutes in expected_minutes.items():
            if self.char1.has_effect("true_sight"):
                self.char1.remove_named_effect("true_sight")
            self.char1.db.class_skill_mastery_levels = {"divine_revelation": tier}
            self.char1.mana = 100
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertTrue(success)
            self.assertIn(str(minutes), result["first"],
                          f"Tier {tier} message should mention {minutes}")

    def test_mana_cost_scales_with_tier(self):
        """Mana cost: SKILLED=5, EXPERT=10, MASTER=15, GM=20."""
        expected = {2: 5, 3: 10, 4: 15, 5: 20}
        for tier, cost in expected.items():
            if self.char1.has_effect("true_sight"):
                self.char1.remove_named_effect("true_sight")
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
        self.char1.mana = 4
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

    def test_message_says_hidden_things(self):
        """Cast message should say 'hidden things' at all tiers."""
        for tier in (2, 3, 4, 5):
            if self.char1.has_effect("true_sight"):
                self.char1.remove_named_effect("true_sight")
            self.char1.db.class_skill_mastery_levels = {"divine_revelation": tier}
            self.char1.mana = 100
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertIn("hidden things", result["first"],
                          f"Tier {tier} message should mention hidden things")
            self.assertNotIn("traps", result["first"],
                             f"Tier {tier} should NOT mention traps")
            self.assertNotIn("invisible", result["first"],
                             f"Tier {tier} should NOT mention invisible")

    def test_divine_themed_messages(self):
        """Messages should reference divine light (school flavour)."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertIn("divine", result["first"].lower())
        self.assertIn("divine", result["third"].lower())

    # --- Hidden visibility (parity with True Sight) ---

    def test_hidden_character_visible_with_holy_sight(self):
        """A character with Holy Sight should see HIDDEN characters in room display."""
        from typeclasses.terrain.rooms.room_base import RoomBase
        room = create_object(RoomBase, key="TestRoom", nohome=True)
        room.always_lit = True
        self.char1.location = room
        self.char2.location = room
        self.spell.cast(self.char1, self.char1)
        self.char2.add_condition(Condition.HIDDEN)
        display = room.get_display_characters(self.char1)
        self.assertIn(self.char2.key, display)

    def test_hidden_character_not_visible_without_holy_sight(self):
        """A character without Holy Sight should NOT see HIDDEN characters."""
        from typeclasses.terrain.rooms.room_base import RoomBase
        room = create_object(RoomBase, key="TestRoom", nohome=True)
        room.always_lit = True
        self.char1.location = room
        self.char2.location = room
        self.char2.add_condition(Condition.HIDDEN)
        display = room.get_display_characters(self.char1)
        self.assertNotIn(self.char2.key, display)

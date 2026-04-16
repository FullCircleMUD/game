"""
Tests for the divine revelation spell school.

Tests:
    - Holy Insight: divine sight, alignment/evil/undead detection, actor identification
    - Holy Sight: self-buff, tiered visibility (traps/invisible/hidden), anti-stacking

evennia test --settings settings tests.spell_tests.test_divine_revelation
"""

from unittest.mock import patch

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
        self.assertEqual(self.spell.target_type, "items_inventory_then_all_room")

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

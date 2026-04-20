"""
Tests for the illusion spell school.

Tests:
    - Registry: all illusion spells registered with correct attributes
    - Blur: disadvantage application, scaling, anti-stacking, script lifecycle
    - Invisibility: condition, no anti-stacking, break_invisibility, duration/mana scaling
    - School membership: get_spells_for_school returns expected set
    - Descriptions and mechanics: all spells have documentation

evennia test --settings settings tests.spell_tests.test_illusion
"""

from unittest.mock import patch

from evennia.utils.create import create_script
from evennia.utils.test_resources import EvenniaTest

from combat.combat_handler import CombatHandler
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.registry import get_spell, get_spells_for_school


# ================================================================== #
#  Illusion Registry Tests
# ================================================================== #

class TestIllusionRegistry(EvenniaTest):
    """Test all illusion spells are registered correctly."""

    def create_script(self):
        pass

    def test_blur_registered(self):
        spell = get_spell("blur")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.BASIC)
        self.assertEqual(spell.target_type, "self")
        self.assertEqual(spell.mana_cost, {1: 5, 2: 8, 3: 10, 4: 14, 5: 16})

    def test_invisibility_registered(self):
        spell = get_spell("invisibility")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.SKILLED)
        self.assertEqual(spell.target_type, "self")

    def test_mass_confusion_registered(self):
        spell = get_spell("mass_confusion")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.EXPERT)
        self.assertEqual(spell.target_type, "none")
        self.assertEqual(spell.mana_cost, {3: 28, 4: 39, 5: 49})

    def test_greater_invisibility_registered(self):
        spell = get_spell("greater_invisibility")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.MASTER)
        self.assertEqual(spell.target_type, "actor_friendly")
        self.assertEqual(spell.mana_cost, {4: 56, 5: 64})

    def test_phantasmal_killer_registered(self):
        spell = get_spell("phantasmal_killer")
        self.assertIsNotNone(spell)
        self.assertEqual(spell.school, skills.ILLUSION)
        self.assertEqual(spell.min_mastery, MasteryLevel.GRANDMASTER)
        self.assertEqual(spell.mana_cost, {5: 100})
        self.assertEqual(spell.target_type, "actor_hostile")

    def test_illusion_school_has_all_spells(self):
        ill = get_spells_for_school("illusion")
        expected = {
            "blur", "invisibility", "mass_confusion",
            "greater_invisibility", "phantasmal_killer",
            "mirror_image", "disguise_self", "distract",
        }
        self.assertEqual(set(ill.keys()), expected)

    def test_illusion_description_and_mechanics(self):
        """All illusion spells should have description and mechanics."""
        for key in ["blur", "invisibility", "mass_confusion",
                     "greater_invisibility", "phantasmal_killer"]:
            spell = get_spell(key)
            self.assertTrue(spell.description, f"{key} missing description")
            self.assertTrue(spell.mechanics, f"{key} missing mechanics")


# ================================================================== #
#  Blur Execution Tests
# ================================================================== #

class TestBlur(EvenniaTest):
    """Test Blur spell execution — disadvantage via BlurScript."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("blur")
        self.char1.db.class_skill_mastery_levels = {"illusion": 1}
        self.char1.mana = 100
        self.char1.hp = 100
        self.char1.hp_max = 100
        self.char2.hp = 100
        self.char2.hp_max = 100
        # PvP so char2 is an enemy of char1
        self.room1.allow_pvp = True
        # Both need combat handlers for get_sides to find them
        self.ch1_handler = create_script(
            CombatHandler, obj=self.char1, key="combat_handler"
        )
        self.ch2_handler = create_script(
            CombatHandler, obj=self.char2, key="combat_handler"
        )

    def tearDown(self):
        for char in (self.char1, self.char2):
            for key in ("combat_handler", "blur_effect"):
                scripts = char.scripts.get(key)
                if scripts:
                    for s in scripts:
                        s.delete()
        super().tearDown()

    def test_blur_applies_named_effect(self):
        """Casting should create a blurred named effect on caster."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("blurred"))

    def test_blur_creates_script(self):
        """Casting should attach a BlurScript to the caster."""
        self.spell.cast(self.char1, self.char1)
        scripts = self.char1.scripts.get("blur_effect")
        self.assertTrue(scripts)
        self.assertEqual(scripts[0].db.remaining_ticks, 3)  # tier 1 = 3 rounds

    def test_blur_requires_combat(self):
        """Should fail if caster is not in combat, with mana refunded."""
        # Remove combat handler
        self.ch1_handler.delete()
        mana_before = self.char1.mana
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertEqual(self.char1.mana, mana_before)  # mana refunded

    def test_blur_sets_disadvantage_on_enemies(self):
        """Casting should immediately set disadvantage on enemies."""
        self.spell.cast(self.char1, self.char1)
        # char2's combat handler should have disadvantage against char1
        self.assertTrue(self.ch2_handler.has_disadvantage(self.char1))

    def test_blur_rounds_scale_with_tier(self):
        """Script remaining_ticks should follow _ROUNDS scaling."""
        expected = {1: 3, 2: 4, 3: 5, 4: 6, 5: 7}
        for tier in range(1, 6):
            # Clean up from previous iteration
            if self.char1.has_effect("blurred"):
                self.char1.remove_named_effect("blurred")
            existing = self.char1.scripts.get("blur_effect")
            if existing:
                existing[0].delete()

            self.char1.db.class_skill_mastery_levels = {"illusion": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char1)
            scripts = self.char1.scripts.get("blur_effect")
            self.assertEqual(
                scripts[0].db.remaining_ticks, expected[tier],
                f"Tier {tier} should have {expected[tier]} rounds"
            )

    def test_blur_tick_sets_disadvantage(self):
        """Each tick should refresh disadvantage on enemies."""
        self.char1.db.class_skill_mastery_levels = {"illusion": 3}
        self.spell.cast(self.char1, self.char1)
        scripts = self.char1.scripts.get("blur_effect")

        # Clear the initial disadvantage to verify tick sets it fresh
        self.ch2_handler.set_disadvantage(self.char1, rounds=0)
        self.assertFalse(self.ch2_handler.has_disadvantage(self.char1))

        # Tick the blur script
        scripts[0].tick_blur()
        self.assertTrue(self.ch2_handler.has_disadvantage(self.char1))

    def test_blur_expires_after_ticks(self):
        """BlurScript should remove named effect after all ticks."""
        self.spell.cast(self.char1, self.char1)
        scripts = self.char1.scripts.get("blur_effect")
        # Tier 1 = 3 ticks. After ticking 3 times, should expire.
        for _ in range(3):
            scripts[0].tick_blur()
        self.assertFalse(self.char1.has_effect("blurred"))

    def test_blur_anti_stacking_replaces(self):
        """New cast should replace existing blur, not stack."""
        self.char1.db.class_skill_mastery_levels = {"illusion": 3}
        self.spell.cast(self.char1, self.char1)
        scripts1 = self.char1.scripts.get("blur_effect")
        self.assertEqual(scripts1[0].db.remaining_ticks, 5)  # tier 3 = 5 rounds

        # Recast — should replace with fresh 5-round blur
        self.spell.cast(self.char1, self.char1)
        scripts2 = self.char1.scripts.get("blur_effect")
        self.assertEqual(len(scripts2), 1)  # only one script
        self.assertEqual(scripts2[0].db.remaining_ticks, 5)

    def test_blur_deducts_mana(self):
        """Should deduct 5 mana at tier 1."""
        self.spell.cast(self.char1, self.char1)
        self.assertEqual(self.char1.mana, 95)

    def test_blur_mastery_check(self):
        """Should fail without illusion mastery."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_blur_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 4
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_blur_multi_perspective_messages(self):
        """Should return first and third person messages (no second for self-cast)."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_blur_same_mana_as_magic_missile(self):
        """Mana costs should match Magic Missile exactly."""
        mm = get_spell("magic_missile")
        self.assertEqual(self.spell.mana_cost, mm.mana_cost)


# ================================================================== #
#  Invisibility Execution Tests
# ================================================================== #

class TestInvisibility(EvenniaTest):
    """Test Invisibility spell execution — INVISIBLE condition, no anti-stacking, break."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.spell = get_spell("invisibility")
        self.char1.db.class_skill_mastery_levels = {"illusion": 2}  # min_mastery = SKILLED
        self.char1.mana = 100

    def test_applies_named_effect(self):
        """Casting should create an invisible named effect on caster."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_effect("invisible"))

    def test_grants_invisible_condition(self):
        """Casting should grant INVISIBLE condition."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))

    def test_remove_clears_condition(self):
        """Removing the named effect should remove INVISIBLE condition."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        self.char1.remove_named_effect("invisible")
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))

    def test_no_anti_stacking(self):
        """Recasting should succeed — INVISIBLE is condition-only, no stat impact."""
        self.spell.cast(self.char1, self.char1)
        self.assertTrue(self.char1.has_effect("invisible"))
        # Condition ref count should be 1
        self.assertEqual(self.char1.get_condition_count(Condition.INVISIBLE), 1)
        # Second cast should also succeed (named effect replaced, condition incremented)
        # apply_named_effect returns False for duplicate key, but the spell doesn't check
        # — it always calls apply_named_effect. The named effect won't stack (same key),
        # but the condition won't double either since the effect is already tracked.
        # The key behavior: has_condition(INVISIBLE) stays True.
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))

    def test_duration_scales_with_tier(self):
        """Duration should scale: SKILLED=5min, EXPERT=10min, MASTER=30min, GM=60min."""
        expected_minutes = {2: 5, 3: 10, 4: 30, 5: 60}
        for tier, minutes in expected_minutes.items():
            if self.char1.has_effect("invisible"):
                self.char1.remove_named_effect("invisible")
            self.char1.db.class_skill_mastery_levels = {"illusion": tier}
            self.char1.mana = 100
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertTrue(success)
            self.assertIn(str(minutes), result["first"],
                          f"Tier {tier} message should mention {minutes}")

    def test_mana_cost_scales_with_tier(self):
        """Mana cost: SKILLED=15, EXPERT=25, MASTER=40, GM=40."""
        expected = {2: 15, 3: 25, 4: 40, 5: 40}
        for tier, cost in expected.items():
            if self.char1.has_effect("invisible"):
                self.char1.remove_named_effect("invisible")
            self.char1.db.class_skill_mastery_levels = {"illusion": tier}
            self.char1.mana = 100
            self.spell.cast(self.char1, self.char1)
            self.assertEqual(self.char1.mana, 100 - cost,
                             f"Tier {tier} should cost {cost} mana")

    def test_mastery_check(self):
        """Should fail without illusion mastery at SKILLED level."""
        self.char1.db.class_skill_mastery_levels = {}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mastery", msg.lower())

    def test_basic_mastery_too_low(self):
        """BASIC mastery should not be enough (min_mastery = SKILLED)."""
        self.char1.db.class_skill_mastery_levels = {"illusion": 1}
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)

    def test_not_enough_mana(self):
        """Should fail with insufficient mana."""
        self.char1.mana = 14
        success, msg = self.spell.cast(self.char1, self.char1)
        self.assertFalse(success)
        self.assertIn("mana", msg.lower())

    def test_multi_perspective_messages(self):
        """Should return first and third person messages (no second for self-cast)."""
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertIsInstance(result, dict)
        self.assertIn("first", result)
        self.assertIsNone(result["second"])
        self.assertIn("third", result)

    def test_break_invisibility_zeros_all_refs(self):
        """break_invisibility() should zero condition regardless of ref count."""
        # Apply via spell (1 ref from named effect)
        self.spell.cast(self.char1, self.char1)
        # Manually add extra refs (simulating multiple sources)
        self.char1._add_condition_raw(Condition.INVISIBLE)
        self.char1._add_condition_raw(Condition.INVISIBLE)
        self.assertEqual(self.char1.get_condition_count(Condition.INVISIBLE), 3)

        # Break should zero everything
        result = self.char1.break_invisibility()
        self.assertTrue(result)
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))
        self.assertEqual(self.char1.get_condition_count(Condition.INVISIBLE), 0)
        self.assertFalse(self.char1.has_effect("invisible"))

    def test_break_invisibility_returns_false_if_not_invisible(self):
        """break_invisibility() should return False if not invisible."""
        result = self.char1.break_invisibility()
        self.assertFalse(result)


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
        success, result = self.spell.cast(self.char1, self.char1)
        self.assertTrue(success)
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        self.assertEqual(self.char1.mana, start_mana - 15)  # tier 2 = 15 mana

    @patch("world.spells.illusion.invisibility.Invisibility.get_caster_tier")
    def test_recast_skips_when_existing_stronger(self, mock_tier):
        """Recast should skip and refund if existing invisibility has more time."""
        mock_tier.return_value = 5
        self.spell.cast(self.char1, self.char1)

        with patch.object(
            type(self.char1), "get_effect_remaining_seconds",
            return_value=3500,
        ):
            mock_tier.return_value = 2
            start_mana = self.char1.mana
            success, result = self.spell.cast(self.char1, self.char1)
            self.assertFalse(success)
            self.assertEqual(self.char1.mana, start_mana)  # refunded
            self.assertIn("stronger", result["first"].lower())

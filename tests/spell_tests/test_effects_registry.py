"""
Tests for the NamedEffect registry, convenience methods, break_effect,
and registry auto-fill.

Run with:
    evennia test --settings settings tests.spell_tests.test_effects_registry
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
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

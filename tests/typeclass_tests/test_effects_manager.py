"""
Tests for EffectsManagerMixin — unified effect system.

Covers:
  - Layer 1: condition flags (backward compat with old ConditionsMixin tests)
  - Layer 2: stat effect dispatch (apply_effect/remove_effect)
  - Layer 3: named effects (apply, remove, anti-stacking, tick, clear)
  - Combat integration: stun/prone via named effects, Shield reactive spell
  - Backward compatibility: equipment wear_effects, direct add_condition

evennia test --settings settings tests.typeclass_tests.test_effects_manager
"""

from unittest.mock import MagicMock, patch, PropertyMock

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create

from enums.condition import Condition
from enums.named_effect import NamedEffect


class TestNamedEffects(EvenniaTest):
    """Core named effect lifecycle tests."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── apply_named_effect ────────────────────────────────────

    def test_apply_named_effect_returns_true(self):
        """First application of a named effect should return True."""
        result = self.char1.apply_named_effect(
            key="stunned",
            duration=2,
            duration_type="combat_rounds",
            messages={"start": "Buff starts.", "end": "Buff ends."},
        )
        self.assertTrue(result)
        self.assertTrue(self.char1.has_effect("stunned"))

    def test_apply_named_effect_anti_stacking(self):
        """Applying the same named effect twice should return False (anti-stacking)."""
        self.char1.apply_named_effect(key="stunned", duration=2, duration_type="combat_rounds")
        result = self.char1.apply_named_effect(key="stunned", duration=5, duration_type="combat_rounds")
        self.assertFalse(result)
        # Duration should NOT be overwritten
        record = self.char1.get_named_effect("stunned")
        self.assertEqual(record["duration"], 2)

    def test_apply_with_condition_flag(self):
        """Named effect with condition=Condition.SLOWED should set the flag."""
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        self.assertTrue(self.char1.has_condition(Condition.SLOWED))

    def test_apply_with_stat_effects(self):
        """Named effect with stat effects should modify the stat."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=2,
            duration_type="combat_rounds",
        )
        self.assertEqual(self.char1.armor_class, original_ac + 4)

    def test_apply_sends_start_message(self):
        """Named effect with start message should msg the character."""
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.apply_named_effect(
                key="stunned",
                messages={"start": "You feel stronger!"},
            )
            mock_msg.assert_called_once_with("You feel stronger!")

    def test_apply_sends_third_person_message(self):
        """Named effect with start_third should broadcast to room."""
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.apply_named_effect(
                key="stunned",
                messages={
                    "start": "You feel stronger!",
                    "start_third": "{name} glows with power!",
                },
            )
            mock_msg.assert_called_once()
            msg_text = mock_msg.call_args[1].get("text", ("",))[0]
            self.assertIn("Char", msg_text)

    def test_apply_rejects_unknown_key(self):
        """Applying an effect with an unregistered key should raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.char1.apply_named_effect(key="totally_fake_effect")
        self.assertIn("Unknown named effect", str(ctx.exception))
        self.assertIn("enums/named_effect.py", str(ctx.exception))

    # ── remove_named_effect ───────────────────────────────────

    def test_remove_named_effect_returns_true(self):
        """Removing an active named effect should return True."""
        self.char1.apply_named_effect(key="stunned", duration=2, duration_type="combat_rounds")
        result = self.char1.remove_named_effect("stunned")
        self.assertTrue(result)
        self.assertFalse(self.char1.has_effect("stunned"))

    def test_remove_named_effect_not_found(self):
        """Removing a non-existent effect should return False."""
        result = self.char1.remove_named_effect("nonexistent")
        self.assertFalse(result)

    def test_remove_reverses_condition_flag(self):
        """Removing a named effect should clear its condition flag."""
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.remove_named_effect("slowed")
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))

    def test_remove_reverses_stat_effects(self):
        """Removing a named effect should reverse stat modifications."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=2,
            duration_type="combat_rounds",
        )
        self.char1.remove_named_effect("shield")
        self.assertEqual(self.char1.armor_class, original_ac)

    def test_remove_sends_end_message(self):
        """Removing a named effect should send end messages."""
        self.char1.apply_named_effect(
            key="stunned",
            messages={"start": "Start!", "end": "End!"},
        )
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.remove_named_effect("stunned")
            mock_msg.assert_called_once_with("End!")

    def test_remove_sends_third_person_end_message(self):
        """Removing a named effect should broadcast end message to room."""
        self.char1.apply_named_effect(
            key="stunned",
            messages={"start": "S", "end": "E", "end_third": "{name} stops glowing."},
        )
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.remove_named_effect("stunned")
            mock_msg.assert_called_once()

    # ── has_effect ────────────────────────────────────────────

    def test_has_effect_true(self):
        """has_effect returns True for active effects."""
        self.char1.apply_named_effect(key="stunned")
        self.assertTrue(self.char1.has_effect("stunned"))

    def test_has_effect_false(self):
        """has_effect returns False for inactive effects."""
        self.assertFalse(self.char1.has_effect("nonexistent"))

    # ── get_named_effect ──────────────────────────────────────

    def test_get_named_effect_returns_record(self):
        """get_named_effect returns the full effect record."""
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=2,
            duration_type="combat_rounds",
        )
        record = self.char1.get_named_effect("shield")
        self.assertIsNotNone(record)
        self.assertEqual(record["duration"], 2)
        self.assertEqual(record["duration_type"], "combat_rounds")

    def test_get_named_effect_none_when_inactive(self):
        """get_named_effect returns None for inactive effects."""
        self.assertIsNone(self.char1.get_named_effect("nonexistent"))


class TestCombatRoundTicking(EvenniaTest):
    """Tests for tick_combat_round() lifecycle management."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_tick_decrements_duration(self):
        """tick_combat_round should decrement duration by 1."""
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.tick_combat_round()
        record = self.char1.get_named_effect("shield")
        self.assertEqual(record["duration"], 2)

    def test_tick_removes_expired_effects(self):
        """tick_combat_round should remove effects when duration reaches 0."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=1,
            duration_type="combat_rounds",
            messages={"end": "Shield fades."},
        )
        self.assertEqual(self.char1.armor_class, original_ac + 4)

        self.char1.tick_combat_round()

        self.assertFalse(self.char1.has_effect("shield"))
        self.assertEqual(self.char1.armor_class, original_ac)

    def test_tick_removes_expired_condition_flag(self):
        """Expired combat round effect should clear its condition flag."""
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=1,
            duration_type="combat_rounds",
        )
        self.assertTrue(self.char1.has_condition(Condition.SLOWED))
        self.char1.tick_combat_round()
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))

    def test_tick_does_not_affect_seconds_effects(self):
        """tick_combat_round should not decrement seconds-based effects."""
        # Using "shield" key with seconds duration — testing tick mechanism,
        # not Shield-specific behaviour
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
            duration=300,
            duration_type="seconds",
        )
        self.char1.tick_combat_round()
        record = self.char1.get_named_effect("shield")
        self.assertEqual(record["duration"], 300)

    def test_tick_does_not_affect_permanent_effects(self):
        """tick_combat_round should not touch permanent effects (duration=None)."""
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
        )
        self.char1.tick_combat_round()
        self.assertTrue(self.char1.has_effect("slowed"))

    def test_multiple_ticks_countdown(self):
        """Multiple ticks should count down correctly."""
        self.char1.apply_named_effect(
            key="stunned",
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.tick_combat_round()  # 2 remaining
        self.assertTrue(self.char1.has_effect("stunned"))
        self.char1.tick_combat_round()  # 1 remaining
        self.assertTrue(self.char1.has_effect("stunned"))
        self.char1.tick_combat_round()  # 0 → removed
        self.assertFalse(self.char1.has_effect("stunned"))


class TestClearCombatEffects(EvenniaTest):
    """Tests for clear_combat_effects() — combat end cleanup."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_clear_removes_combat_round_effects(self):
        """clear_combat_effects should remove all combat_rounds effects."""
        self.char1.apply_named_effect(key="stunned", duration=2, duration_type="combat_rounds")
        self.char1.apply_named_effect(key="shield", duration=3, duration_type="combat_rounds",
                                       effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}])
        self.char1.clear_combat_effects()
        self.assertFalse(self.char1.has_effect("stunned"))
        self.assertFalse(self.char1.has_effect("shield"))

    def test_clear_reverses_stat_effects(self):
        """clear_combat_effects should reverse stat modifications."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 5}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.clear_combat_effects()
        self.assertEqual(self.char1.armor_class, original_ac)

    def test_clear_reverses_condition_flags(self):
        """clear_combat_effects should clear condition flags from combat effects."""
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.clear_combat_effects()
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))

    def test_clear_preserves_non_combat_effects(self):
        """clear_combat_effects should NOT remove seconds-based or permanent effects."""
        # Using real keys with non-standard duration types — testing mechanism
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
            duration=300,
            duration_type="seconds",
        )
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration_type=None,  # explicit override — registry defaults to combat_rounds
        )
        self.char1.clear_combat_effects()
        self.assertTrue(self.char1.has_effect("shield"))
        self.assertTrue(self.char1.has_effect("slowed"))
        self.assertTrue(self.char1.has_condition(Condition.SLOWED))


class TestStunProneNamedEffects(EvenniaTest):
    """Tests for stun/prone as named effects (action denial in combat)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_stunned_via_named_effect(self):
        """Stun applied via named effect should be checkable with has_effect."""
        self.char1.apply_named_effect(
            key="stunned",
            duration=1,
            duration_type="combat_rounds",
            messages={
                "start": NamedEffect.STUNNED.get_start_message(),
                "end": NamedEffect.STUNNED.get_end_message(),
            },
        )
        self.assertTrue(self.char1.has_effect("stunned"))

    def test_stunned_expires_after_tick(self):
        """Stun with duration=1 should expire after one tick."""
        self.char1.apply_named_effect(
            key="stunned",
            duration=1,
            duration_type="combat_rounds",
        )
        self.char1.tick_combat_round()
        self.assertFalse(self.char1.has_effect("stunned"))

    def test_prone_via_named_effect(self):
        """Prone applied via named effect should be checkable with has_effect."""
        self.char1.apply_named_effect(
            key="prone",
            duration=1,
            duration_type="combat_rounds",
            messages={
                "start": NamedEffect.PRONE.get_start_message(),
                "end": NamedEffect.PRONE.get_end_message(),
            },
        )
        self.assertTrue(self.char1.has_effect("prone"))

    def test_prone_expires_after_tick(self):
        """Prone with duration=1 should expire after one tick."""
        self.char1.apply_named_effect(
            key="prone",
            duration=1,
            duration_type="combat_rounds",
        )
        self.char1.tick_combat_round()
        self.assertFalse(self.char1.has_effect("prone"))

    def test_gm_stun_two_rounds(self):
        """GM unarmed stun (2 rounds) should last 2 ticks."""
        self.char1.apply_named_effect(
            key="stunned",
            duration=2,
            duration_type="combat_rounds",
        )
        self.char1.tick_combat_round()
        self.assertTrue(self.char1.has_effect("stunned"))
        self.char1.tick_combat_round()
        self.assertFalse(self.char1.has_effect("stunned"))

    def test_stun_cleared_on_combat_end(self):
        """Stun should be removed when clear_combat_effects is called."""
        self.char1.apply_named_effect(
            key="stunned",
            duration=5,
            duration_type="combat_rounds",
        )
        self.char1.clear_combat_effects()
        self.assertFalse(self.char1.has_effect("stunned"))

    def test_stun_anti_stacking(self):
        """Cannot double-stun — second apply returns False."""
        self.char1.apply_named_effect(key="stunned", duration=1, duration_type="combat_rounds")
        result = self.char1.apply_named_effect(key="stunned", duration=2, duration_type="combat_rounds")
        self.assertFalse(result)
        # Duration should still be 1, not overwritten
        record = self.char1.get_named_effect("stunned")
        self.assertEqual(record["duration"], 1)


class TestShieldNamedEffect(EvenniaTest):
    """Tests for Shield spell as a named effect."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_shield_applies_ac_bonus(self):
        """Shield named effect should boost armor_class."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=2,
            duration_type="combat_rounds",
            messages={"start": "Shield!"},
        )
        self.assertEqual(self.char1.armor_class, original_ac + 4)

    def test_shield_anti_stacking(self):
        """Cannot double-shield — has_effect blocks second apply."""
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=2,
            duration_type="combat_rounds",
        )
        result = self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 6}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.assertFalse(result)

    def test_shield_expires_and_reverses_ac(self):
        """Shield should reverse AC bonus when it expires via tick."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=1,
            duration_type="combat_rounds",
        )
        self.char1.tick_combat_round()
        self.assertFalse(self.char1.has_effect("shield"))
        self.assertEqual(self.char1.armor_class, original_ac)

    def test_shield_cleared_on_combat_end(self):
        """Shield should be removed on combat end."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 5}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.clear_combat_effects()
        self.assertFalse(self.char1.has_effect("shield"))
        self.assertEqual(self.char1.armor_class, original_ac)

    def test_shield_reapply_after_expiry(self):
        """Shield should be reapplicable after expiry."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=1,
            duration_type="combat_rounds",
        )
        self.char1.tick_combat_round()
        self.assertFalse(self.char1.has_effect("shield"))

        # Re-apply
        result = self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=1,
            duration_type="combat_rounds",
        )
        self.assertTrue(result)
        self.assertEqual(self.char1.armor_class, original_ac + 4)


class TestBackwardCompatibility(EvenniaTest):
    """Tests that old code paths still work after ConditionsMixin → EffectsManagerMixin."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── Direct condition API (same as old ConditionsMixin) ────

    def test_add_condition_still_works(self):
        """Direct add_condition should work as before."""
        result = self.char1.add_condition(Condition.DARKVISION)
        self.assertTrue(result)
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))

    def test_remove_condition_still_works(self):
        """Direct remove_condition should work as before."""
        self.char1.add_condition(Condition.HASTED)
        result = self.char1.remove_condition(Condition.HASTED)
        self.assertTrue(result)
        self.assertFalse(self.char1.has_condition(Condition.HASTED))

    def test_ref_counting_still_works(self):
        """Ref counting should work as before."""
        self.char1.add_condition(Condition.DARKVISION)
        self.char1.add_condition(Condition.DARKVISION)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 2)
        self.char1.remove_condition(Condition.DARKVISION)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 1)
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))

    def test_string_and_enum_interchangeable(self):
        """Both Condition enum and string should work interchangeably."""
        self.char1.add_condition(Condition.DARKVISION)
        self.assertTrue(self.char1.has_condition("darkvision"))
        self.char1.add_condition("darkvision")
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 2)

    # ── apply_effect / remove_effect (stat bonuses) ───────────

    def test_apply_effect_stat_bonus(self):
        """apply_effect with stat_bonus should still work."""
        original_ac = self.char1.armor_class
        self.char1.apply_effect({"type": "stat_bonus", "stat": "armor_class", "value": 2})
        self.assertEqual(self.char1.armor_class, original_ac + 2)

    def test_remove_effect_stat_bonus(self):
        """remove_effect with stat_bonus should reverse the bonus."""
        original_ac = self.char1.armor_class
        effect = {"type": "stat_bonus", "stat": "armor_class", "value": 2}
        self.char1.apply_effect(effect)
        self.char1.remove_effect(effect)
        self.assertEqual(self.char1.armor_class, original_ac)

    def test_apply_effect_condition(self):
        """apply_effect with condition type should set the condition flag."""
        self.char1.apply_effect({"type": "condition", "condition": "darkvision"})
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))

    def test_remove_effect_condition(self):
        """remove_effect with condition type should clear the condition flag."""
        self.char1.apply_effect({"type": "condition", "condition": "darkvision"})
        self.char1.remove_effect({"type": "condition", "condition": "darkvision"})
        self.assertFalse(self.char1.has_condition(Condition.DARKVISION))

    # ── Named effect + direct condition coexistence ───────────

    def test_named_effect_condition_independent_of_direct_condition(self):
        """Named effect condition flag and direct add_condition are independent ref counts."""
        # Named effect adds SLOWED (via _add_condition_raw, count=1)
        self.char1.apply_named_effect(
            key="slowed",
            condition=Condition.SLOWED,
            duration=3,
            duration_type="combat_rounds",
        )
        # Direct add_condition adds another SLOWED source (count=2)
        self.char1.add_condition(Condition.SLOWED)
        self.assertEqual(self.char1.get_condition_count(Condition.SLOWED), 2)

        # Remove named effect (count goes back to 1)
        self.char1.remove_named_effect("slowed")
        self.assertTrue(self.char1.has_condition(Condition.SLOWED))
        self.assertEqual(self.char1.get_condition_count(Condition.SLOWED), 1)

        # Remove remaining direct condition
        self.char1.remove_condition(Condition.SLOWED)
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))


class TestNamedEffectVisibilityFiltering(EvenniaTest):
    """Tests that named effect messages respect HIDDEN/INVISIBLE visibility."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_hidden_suppresses_third_person_start(self):
        """Named effect start_third should not reach room when actor is HIDDEN."""
        self.char1.add_condition(Condition.HIDDEN)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.apply_named_effect(
                key="stunned",
                messages={"start": "S", "start_third": "{name} glows!"},
            )
            mock_msg.assert_not_called()

    def test_hidden_still_gets_first_person(self):
        """Hidden actor should still receive their own first-person message."""
        self.char1.add_condition(Condition.HIDDEN)
        with patch.object(self.char1, "msg") as mock_msg:
            self.char1.apply_named_effect(
                key="stunned",
                messages={"start": "You glow!"},
            )
            mock_msg.assert_called_once_with("You glow!")

    def test_invisible_filters_start_third(self):
        """Named effect start_third should be filtered by INVISIBLE (requires DETECT_INVIS)."""
        self.char1.add_condition(Condition.INVISIBLE)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.apply_named_effect(
                key="stunned",
                messages={"start": "S", "start_third": "{name} glows!"},
            )
            mock_msg.assert_not_called()

    def test_invisible_visible_with_detect_invis(self):
        """Named effect start_third should reach recipients with DETECT_INVIS."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.char2.add_condition(Condition.DETECT_INVIS)
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.apply_named_effect(
                key="stunned",
                messages={"start": "S", "start_third": "{name} glows!"},
            )
            mock_msg.assert_called_once()

    def test_hidden_suppresses_third_person_end(self):
        """Named effect end_third should not reach room when actor is HIDDEN."""
        self.char1.add_condition(Condition.HIDDEN)
        self.char1.apply_named_effect(
            key="stunned",
            messages={"end": "E", "end_third": "{name} stops."},
        )
        with patch.object(self.char2, "msg") as mock_msg:
            self.char1.remove_named_effect("stunned")
            mock_msg.assert_not_called()


class TestMultipleEffectsInteraction(EvenniaTest):
    """Tests for multiple simultaneous named effects."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_multiple_effects_coexist(self):
        """Multiple named effects should coexist independently."""
        original_ac = self.char1.armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=2,
            duration_type="combat_rounds",
        )
        self.char1.apply_named_effect(
            key="stunned",
            duration=1,
            duration_type="combat_rounds",
        )
        self.assertTrue(self.char1.has_effect("shield"))
        self.assertTrue(self.char1.has_effect("stunned"))
        self.assertEqual(self.char1.armor_class, original_ac + 4)

    def test_tick_handles_different_durations(self):
        """Effects with different durations should expire independently."""
        self.char1.apply_named_effect(key="stunned", duration=1, duration_type="combat_rounds")
        self.char1.apply_named_effect(key="shield", duration=3, duration_type="combat_rounds",
                                       effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}])

        self.char1.tick_combat_round()
        # stunned (1→0) should be gone, shield (3→2) should remain
        self.assertFalse(self.char1.has_effect("stunned"))
        self.assertTrue(self.char1.has_effect("shield"))

        self.char1.tick_combat_round()  # shield: 2→1
        self.assertTrue(self.char1.has_effect("shield"))

        self.char1.tick_combat_round()  # shield: 1→0
        self.assertFalse(self.char1.has_effect("shield"))

    def test_mixed_duration_types_with_clear(self):
        """clear_combat_effects should only remove combat_rounds effects."""
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )
        # Using "slowed" with seconds duration — testing mechanism, not SLOWED-specific
        self.char1.apply_named_effect(
            key="slowed",
            effects=[{"type": "stat_bonus", "stat": "strength", "value": 2}],
            duration=300,
            duration_type="seconds",
        )
        original_str = self.char1.strength

        self.char1.clear_combat_effects()

        # Shield gone, seconds-based slowed remains
        self.assertFalse(self.char1.has_effect("shield"))
        self.assertTrue(self.char1.has_effect("slowed"))
        self.assertEqual(self.char1.strength, original_str)


# ══════════════════════════════════════════════════════════════════════
#  Nuclear Recalculate Tests
# ══════════════════════════════════════════════════════════════════════

def _make_wearable(key, wearslot_value, wear_effects=None, location=None):
    """Create a WearableNFTItem with given wearslot and effects."""
    from evennia.utils import create as ev_create
    from enums.wearslot import HumanoidWearSlot
    obj = ev_create.create_object(
        "typeclasses.items.wearables.wearable_nft_item.WearableNFTItem",
        key=key,
        nohome=True,
    )
    obj.wearslot = wearslot_value
    if wear_effects is not None:
        obj.wear_effects = wear_effects
    if location:
        obj.move_to(location, quiet=True)
    return obj


class TestRecalculateStats(EvenniaTest):
    """Tests for BaseActor._recalculate_stats() — nuclear stat rebuild."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── Basic recalculate ──────────────────────────────────────

    def test_recalculate_no_effects_resets_to_base(self):
        """With no effects active, recalculate should set stats to base values."""
        # Manually dirty some stats
        self.char1.armor_class = 99
        self.char1.total_hit_bonus = 50
        self.char1.strength = 20

        self.char1._recalculate_stats()

        self.assertEqual(self.char1.armor_class, self.char1.base_armor_class)
        self.assertEqual(self.char1.total_hit_bonus, 0)
        self.assertEqual(self.char1.strength, self.char1.base_strength)
        self.assertEqual(self.char1.attacks_per_round, 1)
        self.assertEqual(self.char1.hit_bonuses, {})
        self.assertEqual(self.char1.damage_bonuses, {})

    def test_recalculate_resets_all_ability_scores(self):
        """All six ability scores should reset to base values."""
        for stat in ("strength", "dexterity", "constitution",
                     "intelligence", "wisdom", "charisma"):
            setattr(self.char1, stat, 99)

        self.char1._recalculate_stats()

        for stat in ("strength", "dexterity", "constitution",
                     "intelligence", "wisdom", "charisma"):
            self.assertEqual(
                getattr(self.char1, stat),
                getattr(self.char1, f"base_{stat}"),
                f"{stat} should reset to base_{stat}",
            )

    # ── Equipment effects ──────────────────────────────────────

    def test_recalculate_includes_worn_equipment(self):
        """Worn equipment wear_effects should be included in recalculate."""
        from enums.wearslot import HumanoidWearSlot
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 3}]
        item = _make_wearable("Helm", HumanoidWearSlot.HEAD, effects, self.char1)
        self.char1.wear(item)

        base_ac = self.char1.base_armor_class
        # After wear, AC should be base + 3
        self.assertEqual(self.char1.armor_class, base_ac + 3)

        # Manual recalculate should produce same result
        self.char1._recalculate_stats()
        self.assertEqual(self.char1.armor_class, base_ac + 3)

    def test_recalculate_excludes_removed_equipment(self):
        """After removing equipment, recalculate should not include its effects."""
        from enums.wearslot import HumanoidWearSlot
        effects = [{"type": "stat_bonus", "stat": "armor_class", "value": 5}]
        item = _make_wearable("Shield", HumanoidWearSlot.HOLD, effects, self.char1)
        base_ac = self.char1.base_armor_class

        self.char1.wear(item)
        self.assertEqual(self.char1.armor_class, base_ac + 5)

        self.char1.remove(item)
        self.assertEqual(self.char1.armor_class, base_ac)

    def test_recalculate_multiple_equipment_pieces(self):
        """Multiple worn items should all contribute to recalculate."""
        from enums.wearslot import HumanoidWearSlot
        helm = _make_wearable(
            "Helm", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
            self.char1,
        )
        body = _make_wearable(
            "Mail", HumanoidWearSlot.BODY,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            self.char1,
        )
        base_ac = self.char1.base_armor_class

        self.char1.wear(helm)
        self.char1.wear(body)
        self.assertEqual(self.char1.armor_class, base_ac + 6)

    # ── Named effect stat bonuses ──────────────────────────────

    def test_recalculate_includes_named_effects(self):
        """Active named effects with stat bonuses should be included."""
        base_ac = self.char1.base_armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 4)

        # Manual recalculate should produce same result
        self.char1._recalculate_stats()
        self.assertEqual(self.char1.armor_class, base_ac + 4)

    def test_recalculate_after_named_effect_removed(self):
        """After removing a named effect, its stat bonus should be gone."""
        base_ac = self.char1.base_armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.remove_named_effect("shield")
        self.assertEqual(self.char1.armor_class, base_ac)

    # ── Equipment + named effects stacking ─────────────────────

    def test_recalculate_stacks_equipment_and_named_effects(self):
        """Equipment and named effect bonuses should stack correctly."""
        from enums.wearslot import HumanoidWearSlot
        helm = _make_wearable(
            "Helm", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
            self.char1,
        )
        base_ac = self.char1.base_armor_class

        self.char1.wear(helm)
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )

        self.assertEqual(self.char1.armor_class, base_ac + 6)

        # Remove named effect — equipment bonus remains
        self.char1.remove_named_effect("shield")
        self.assertEqual(self.char1.armor_class, base_ac + 2)

        # Remove equipment — back to base
        self.char1.remove(helm)
        self.assertEqual(self.char1.armor_class, base_ac)

    # ── Racial effects ─────────────────────────────────────────

    def test_recalculate_includes_racial_damage_resistance(self):
        """Racial damage_resistance effects should be rebuilt by recalculate."""
        # Dwarf has 30% poison resistance
        self.char1.race = "dwarf"
        self.char1._recalculate_stats()
        self.assertEqual(self.char1.damage_resistances.get("poison", 0), 30)

    def test_recalculate_racial_plus_equipment_resistance_stacks(self):
        """Racial resistance and equipment resistance should stack."""
        from enums.wearslot import HumanoidWearSlot
        self.char1.race = "dwarf"  # 30% poison resistance
        ring = _make_wearable(
            "Poison Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            [{"type": "damage_resistance", "damage_type": "poison", "value": 20}],
            self.char1,
        )
        self.char1.wear(ring)
        self.assertEqual(self.char1.damage_resistances.get("poison", 0), 50)

    # ── Hit/damage bonus effects ───────────────────────────────

    def test_recalculate_hit_bonus(self):
        """hit_bonus effects should be included in recalculate."""
        from enums.wearslot import HumanoidWearSlot
        gloves = _make_wearable(
            "Gloves", HumanoidWearSlot.HANDS,
            [{"type": "hit_bonus", "weapon_type": "unarmed", "value": 2}],
            self.char1,
        )
        self.char1.wear(gloves)
        self.assertEqual(self.char1.hit_bonuses.get("unarmed", 0), 2)

        self.char1.remove(gloves)
        self.assertEqual(self.char1.hit_bonuses.get("unarmed", 0), 0)

    def test_recalculate_damage_bonus(self):
        """damage_bonus effects should be included in recalculate."""
        from enums.wearslot import HumanoidWearSlot
        belt = _make_wearable(
            "Belt", HumanoidWearSlot.WAIST,
            [{"type": "damage_bonus", "weapon_type": "long_sword", "value": 1}],
            self.char1,
        )
        self.char1.wear(belt)
        self.assertEqual(self.char1.damage_bonuses.get("long_sword", 0), 1)

        self.char1.remove(belt)
        self.assertEqual(self.char1.damage_bonuses.get("long_sword", 0), 0)

    # ── Condition companion effects ────────────────────────────

    def test_recalculate_includes_condition_companion_effects(self):
        """Condition with companion stat effects should be included when active."""
        from enums.wearslot import HumanoidWearSlot
        # Create an item with a condition that has companion stat effects
        boots = _make_wearable(
            "Haste Boots", HumanoidWearSlot.FEET,
            [{"type": "condition", "condition": "hasted",
              "effects": [{"type": "stat_bonus", "stat": "attacks_per_round", "value": 1}]}],
            self.char1,
        )
        self.char1.wear(boots)

        # Condition should be active
        self.assertTrue(self.char1.has_condition("hasted"))
        # Companion effect: +1 attacks_per_round (base is 1)
        self.assertEqual(self.char1.attacks_per_round, 2)

        # Manual recalculate should still produce same result
        self.char1._recalculate_stats()
        self.assertEqual(self.char1.attacks_per_round, 2)

    # ── break_effect triggers recalculate ──────────────────────

    def test_break_effect_recalculates(self):
        """break_effect should trigger recalculate for stat effects."""
        base_ac = self.char1.base_armor_class
        self.char1.apply_named_effect(
            key="mage_armored",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=300,
            duration_type="seconds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 4)

        self.char1.break_effect(NamedEffect.MAGE_ARMORED)
        self.assertEqual(self.char1.armor_class, base_ac)

    # ── Idempotency ────────────────────────────────────────────

    def test_recalculate_is_idempotent(self):
        """Calling _recalculate_stats() multiple times should produce same result."""
        from enums.wearslot import HumanoidWearSlot
        helm = _make_wearable(
            "Helm", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 3}],
            self.char1,
        )
        self.char1.wear(helm)
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "total_hit_bonus", "value": 2}],
            duration=5,
            duration_type="combat_rounds",
        )

        expected_ac = self.char1.armor_class
        expected_hit = self.char1.total_hit_bonus

        # Multiple recalculates should all produce the same values
        for _ in range(5):
            self.char1._recalculate_stats()
            self.assertEqual(self.char1.armor_class, expected_ac)
            self.assertEqual(self.char1.total_hit_bonus, expected_hit)


class TestRecalculateInteractions(EvenniaTest):
    """
    Tests for interactions between the nuclear recalculate system and other
    subsystems: equipment + named effects, tick expiry, clear_combat_effects,
    break_effect with equipment, condition ref-counting, racial effects, etc.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    # ── Named effects survive equipment changes ───────────────

    def test_named_effect_survives_equip(self):
        """Active named effect should persist when equipment is worn."""
        base_ac = self.char1.base_armor_class
        # Apply buff first
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 4)

        # Equip armor — recalculate should keep both
        from enums.wearslot import HumanoidWearSlot
        helm = _make_wearable(
            "Helm", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
            self.char1,
        )
        self.char1.wear(helm)
        self.assertEqual(self.char1.armor_class, base_ac + 6)

        # Remove armor — named effect still there
        self.char1.remove(helm)
        self.assertEqual(self.char1.armor_class, base_ac + 4)
        self.assertTrue(self.char1.has_effect("shield"))

    def test_named_effect_survives_equipment_swap(self):
        """Swapping equipment should preserve active named effect bonuses."""
        from enums.wearslot import HumanoidWearSlot
        base_ac = self.char1.base_armor_class

        helm_a = _make_wearable(
            "Helm A", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
            self.char1,
        )
        helm_b = _make_wearable(
            "Helm B", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 5}],
            self.char1,
        )

        self.char1.wear(helm_a)
        self.char1.apply_named_effect(
            key="mage_armored",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=300,
            duration_type="seconds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 2 + 4)

        # Swap helms — remove then wear
        self.char1.remove(helm_a)
        self.char1.wear(helm_b)
        self.assertEqual(self.char1.armor_class, base_ac + 5 + 4)

    # ── Multiple named effects ────────────────────────────────

    def test_multiple_named_effects_independent_removal(self):
        """Removing one named effect should not affect another."""
        base_ac = self.char1.base_armor_class

        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.apply_named_effect(
            key="mage_armored",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 3}],
            duration=300,
            duration_type="seconds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 7)

        # Remove shield — mage armor survives
        self.char1.remove_named_effect("shield")
        self.assertEqual(self.char1.armor_class, base_ac + 3)
        self.assertTrue(self.char1.has_effect("mage_armored"))

        # Remove mage armor — back to base
        self.char1.remove_named_effect("mage_armored")
        self.assertEqual(self.char1.armor_class, base_ac)

    # ── tick_combat_round expiry recalculates stats ───────────

    def test_tick_combat_round_expiry_recalculates_stats(self):
        """When a combat round effect expires via tick, stats should recalculate."""
        base_ac = self.char1.base_armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=1,
            duration_type="combat_rounds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 4)

        # Tick — duration 1 → 0, effect expires
        self.char1.tick_combat_round()

        self.assertFalse(self.char1.has_effect("shield"))
        self.assertEqual(self.char1.armor_class, base_ac)

    def test_tick_expiry_preserves_other_effects(self):
        """When one combat effect expires, other active effects should remain."""
        base_ac = self.char1.base_armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=1,
            duration_type="combat_rounds",
        )
        self.char1.apply_named_effect(
            key="staggered",
            effects=[{"type": "stat_bonus", "stat": "total_hit_bonus", "value": -2}],
            duration=3,
            duration_type="combat_rounds",
        )

        self.char1.tick_combat_round()

        # Shield expired, staggered still active (duration 3 → 2)
        self.assertFalse(self.char1.has_effect("shield"))
        self.assertTrue(self.char1.has_effect("staggered"))
        self.assertEqual(self.char1.armor_class, base_ac)
        self.assertEqual(self.char1.total_hit_bonus, -2)

    # ── clear_combat_effects recalculates stats ───────────────

    def test_clear_combat_effects_reverses_stat_bonuses(self):
        """clear_combat_effects should remove all combat-rounds effects and recalculate."""
        base_ac = self.char1.base_armor_class
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=3,
            duration_type="combat_rounds",
        )
        self.char1.apply_named_effect(
            key="staggered",
            effects=[{"type": "stat_bonus", "stat": "total_hit_bonus", "value": -2}],
            duration=2,
            duration_type="combat_rounds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 4)
        self.assertEqual(self.char1.total_hit_bonus, -2)

        self.char1.clear_combat_effects()

        self.assertFalse(self.char1.has_effect("shield"))
        self.assertFalse(self.char1.has_effect("staggered"))
        self.assertEqual(self.char1.armor_class, base_ac)
        self.assertEqual(self.char1.total_hit_bonus, 0)

    def test_clear_combat_effects_preserves_seconds_effects(self):
        """Seconds-based effects should survive clear_combat_effects."""
        base_ac = self.char1.base_armor_class
        self.char1.apply_named_effect(
            key="mage_armored",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=300,
            duration_type="seconds",
        )
        self.char1.apply_named_effect(
            key="shield",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 3}],
            duration=2,
            duration_type="combat_rounds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 7)

        self.char1.clear_combat_effects()

        # Combat effect gone, seconds effect survives
        self.assertFalse(self.char1.has_effect("shield"))
        self.assertTrue(self.char1.has_effect("mage_armored"))
        self.assertEqual(self.char1.armor_class, base_ac + 4)

    # ── break_effect with equipment providing same condition ──

    def test_break_effect_preserves_equipment_stats(self):
        """break_effect should remove named effect stats but preserve equipment stats."""
        from enums.wearslot import HumanoidWearSlot
        base_ac = self.char1.base_armor_class

        # Equip armor (+3 AC)
        helm = _make_wearable(
            "Helm", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 3}],
            self.char1,
        )
        self.char1.wear(helm)
        self.assertEqual(self.char1.armor_class, base_ac + 3)

        # Apply mage armor buff (+4 AC)
        self.char1.apply_named_effect(
            key="mage_armored",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
            duration=300,
            duration_type="seconds",
        )
        self.assertEqual(self.char1.armor_class, base_ac + 7)

        # Break the spell — equipment AC remains
        self.char1.break_effect(NamedEffect.MAGE_ARMORED)
        self.assertFalse(self.char1.has_effect("mage_armored"))
        self.assertEqual(self.char1.armor_class, base_ac + 3)

    def test_break_invisibility_with_invis_item_equipped(self):
        """break_effect(INVISIBLE) nukes ALL condition refs including equipment."""
        from enums.wearslot import HumanoidWearSlot
        # Equip ring that grants INVISIBLE condition
        ring = _make_wearable(
            "Invis Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            [{"type": "condition", "condition": "invisible"}],
            self.char1,
        )
        self.char1.wear(ring)
        self.assertTrue(self.char1.has_condition("invisible"))
        self.assertEqual(self.char1.get_condition_count("invisible"), 1)

        # Apply invisibility spell (named effect — adds another ref)
        self.char1.apply_named_effect(
            key="invisible",
            condition=Condition.INVISIBLE,
            effects=[],
            duration=60,
            duration_type="seconds",
        )
        self.assertEqual(self.char1.get_condition_count("invisible"), 2)

        # Break invisibility — nukes ALL refs (attacking breaks all invis)
        self.char1.break_effect(NamedEffect.INVISIBLE)
        self.assertFalse(self.char1.has_condition("invisible"))
        self.assertFalse(self.char1.has_effect("invisible"))

    # ── Racial effects through equipment cycles ───────────────

    def test_racial_resistance_survives_equip_cycles(self):
        """Racial resistance should persist through multiple equip/unequip cycles."""
        from enums.wearslot import HumanoidWearSlot
        self.char1.race = "dwarf"  # 30% poison resistance
        self.char1._recalculate_stats()

        ring = _make_wearable(
            "Poison Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            [{"type": "damage_resistance", "damage_type": "poison", "value": 20}],
            self.char1,
        )

        for _ in range(3):
            self.char1.wear(ring)
            self.assertEqual(self.char1.damage_resistances.get("poison", 0), 50)
            self.char1.remove(ring)
            self.assertEqual(self.char1.damage_resistances.get("poison", 0), 30)

    def test_racial_plus_equipment_plus_named_effect_resistance(self):
        """Triple-source resistance stacking: racial + equipment + named effect."""
        from enums.wearslot import HumanoidWearSlot
        self.char1.race = "dwarf"  # 30% poison resistance

        ring = _make_wearable(
            "Poison Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            [{"type": "damage_resistance", "damage_type": "poison", "value": 20}],
            self.char1,
        )
        self.char1.wear(ring)

        self.char1.apply_named_effect(
            key="resist_poison",
            effects=[{"type": "damage_resistance", "damage_type": "poison", "value": 15}],
            duration=60,
            duration_type="seconds",
        )

        # 30 + 20 + 15 = 65
        self.assertEqual(self.char1.damage_resistances.get("poison", 0), 65)

        # Remove ring — 30 + 15 = 45
        self.char1.remove(ring)
        self.assertEqual(self.char1.damage_resistances.get("poison", 0), 45)

        # Remove named effect — 30
        self.char1.remove_named_effect("resist_poison")
        self.assertEqual(self.char1.damage_resistances.get("poison", 0), 30)

    # ── Condition ref-counting through recalculate ────────────

    def test_condition_ref_count_survives_recalculate(self):
        """Conditions are NOT rebuilt by recalculate — ref counts preserved."""
        from enums.wearslot import HumanoidWearSlot
        item_a = _make_wearable(
            "DV Ring A", HumanoidWearSlot.LEFT_RING_FINGER,
            [{"type": "condition", "condition": "darkvision"},
             {"type": "stat_bonus", "stat": "wisdom", "value": 1}],
            self.char1,
        )
        item_b = _make_wearable(
            "DV Ring B", HumanoidWearSlot.RIGHT_RING_FINGER,
            [{"type": "condition", "condition": "darkvision"},
             {"type": "stat_bonus", "stat": "wisdom", "value": 2}],
            self.char1,
        )

        self.char1.wear(item_a)
        self.char1.wear(item_b)
        base_wis = self.char1.base_wisdom

        self.assertEqual(self.char1.get_condition_count("darkvision"), 2)
        self.assertEqual(self.char1.wisdom, base_wis + 3)

        # Remove one — condition still active, stats correct
        self.char1.remove(item_a)
        self.assertEqual(self.char1.get_condition_count("darkvision"), 1)
        self.assertTrue(self.char1.has_condition("darkvision"))
        self.assertEqual(self.char1.wisdom, base_wis + 2)

        # Remove second — condition gone
        self.char1.remove(item_b)
        self.assertEqual(self.char1.get_condition_count("darkvision"), 0)
        self.assertFalse(self.char1.has_condition("darkvision"))
        self.assertEqual(self.char1.wisdom, base_wis)

    # ── Companion deduplication via _accumulated_companions ───

    def test_accumulated_companions_prevents_double_bonus(self):
        """Two equipment sources of same compound condition: companion counted once."""
        from enums.wearslot import HumanoidWearSlot
        haste_effect = [{"type": "condition", "condition": "hasted",
                         "effects": [{"type": "stat_bonus", "stat": "attacks_per_round", "value": 1}]}]

        boots = _make_wearable("Haste Boots", HumanoidWearSlot.FEET,
                               haste_effect, self.char1)
        ring = _make_wearable("Haste Ring", HumanoidWearSlot.LEFT_RING_FINGER,
                              haste_effect, self.char1)

        self.char1.wear(boots)
        self.char1.wear(ring)

        # Condition ref count 2 but companion effect applied only once
        self.assertEqual(self.char1.get_condition_count("hasted"), 2)
        self.assertEqual(self.char1.attacks_per_round, 2)  # base 1 + 1

        # Explicit recalculate — same result
        self.char1._recalculate_stats()
        self.assertEqual(self.char1.attacks_per_round, 2)

    def test_named_effect_stat_bonus_stacks_with_equipment_companion(self):
        """Named effect's direct stat_bonus stacks with equipment companion bonus.

        Equipment companion effects (nested inside condition type) are
        deduplicated per condition. Named effect stat_bonus entries are
        separate sources and stack additively — this is correct because
        the named effect's effects list contains direct stat bonuses,
        not condition companions.
        """
        from enums.wearslot import HumanoidWearSlot

        boots = _make_wearable(
            "Haste Boots", HumanoidWearSlot.FEET,
            [{"type": "condition", "condition": "hasted",
              "effects": [{"type": "stat_bonus", "stat": "attacks_per_round", "value": 1}]}],
            self.char1,
        )
        self.char1.wear(boots)
        self.assertEqual(self.char1.attacks_per_round, 2)  # base 1 + companion 1

        # Named effect with direct stat_bonus (not a condition companion)
        effects_dict = dict(self.char1.active_effects)
        effects_dict["haste_spell"] = {
            "condition": "hasted",
            "effects": [{"type": "stat_bonus", "stat": "attacks_per_round", "value": 1}],
            "duration": 60,
            "duration_type": "seconds",
            "messages": {},
        }
        self.char1.active_effects = effects_dict
        self.char1._add_condition_raw("hasted")  # ref count 1→2

        # Both stack: equipment companion +1 AND named effect direct +1
        self.char1._recalculate_stats()
        self.assertEqual(self.char1.attacks_per_round, 3)  # base 1 + companion 1 + direct 1

    # ── Potion + equipment stat stacking ──────────────────────

    def test_potion_and_equipment_stat_bonus_stacking(self):
        """Potion (named effect) and equipment stat bonuses should stack."""
        from enums.wearslot import HumanoidWearSlot
        base_str = self.char1.base_strength

        ring = _make_wearable(
            "STR Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            [{"type": "stat_bonus", "stat": "strength", "value": 2}],
            self.char1,
        )
        self.char1.wear(ring)
        self.assertEqual(self.char1.strength, base_str + 2)

        # Potion buff
        self.char1.apply_named_effect(
            key="potion_strength",
            effects=[{"type": "stat_bonus", "stat": "strength", "value": 3}],
            duration=60,
            duration_type="seconds",
        )
        self.assertEqual(self.char1.strength, base_str + 5)

        # Remove ring — potion remains
        self.char1.remove(ring)
        self.assertEqual(self.char1.strength, base_str + 3)

        # Remove potion — back to base
        self.char1.remove_named_effect("potion_strength")
        self.assertEqual(self.char1.strength, base_str)

    # ── Hit/damage bonus dict rebuild across cycles ───────────

    def test_hit_bonus_stacking_multiple_items(self):
        """Multiple items with hit_bonus for same weapon type should stack."""
        from enums.wearslot import HumanoidWearSlot
        gloves = _make_wearable(
            "Gloves", HumanoidWearSlot.HANDS,
            [{"type": "hit_bonus", "weapon_type": "unarmed", "value": 1}],
            self.char1,
        )
        ring = _make_wearable(
            "Ring", HumanoidWearSlot.LEFT_RING_FINGER,
            [{"type": "hit_bonus", "weapon_type": "unarmed", "value": 2}],
            self.char1,
        )

        self.char1.wear(gloves)
        self.char1.wear(ring)
        self.assertEqual(self.char1.hit_bonuses.get("unarmed", 0), 3)

        self.char1.remove(gloves)
        self.assertEqual(self.char1.hit_bonuses.get("unarmed", 0), 2)

        self.char1.remove(ring)
        self.assertEqual(self.char1.hit_bonuses.get("unarmed", 0), 0)

    # ── Effective @property reflects recalculated Tier 2 ──────

    def test_effective_ac_reflects_recalculated_stats(self):
        """effective_ac should use recalculated armor_class + dex modifier."""
        from enums.wearslot import HumanoidWearSlot
        # Set DEX to 14 (modifier +2)
        self.char1.base_dexterity = 14
        self.char1.dexterity = 14
        base_ac = self.char1.base_armor_class

        helm = _make_wearable(
            "Helm", HumanoidWearSlot.HEAD,
            [{"type": "stat_bonus", "stat": "armor_class", "value": 3}],
            self.char1,
        )
        self.char1.wear(helm)

        # effective_ac = armor_class + dex_mod = (base + 3) + 2
        self.assertEqual(self.char1.effective_ac, base_ac + 3 + 2)

        # DEX buff via potion named effect
        self.char1.apply_named_effect(
            key="potion_dexterity",
            effects=[{"type": "stat_bonus", "stat": "dexterity", "value": 4}],
            duration=60,
            duration_type="seconds",
        )
        # DEX now 18 (mod +4), effective_ac = (base + 3) + 4
        self.assertEqual(self.char1.dexterity, 18)
        self.assertEqual(self.char1.effective_ac, base_ac + 3 + 4)

        # Remove DEX buff — back to DEX 14 (mod +2)
        self.char1.remove_named_effect("potion_dexterity")
        self.assertEqual(self.char1.effective_ac, base_ac + 3 + 2)


class TestClearAllEffects(EvenniaTest):
    """Tests for clear_all_effects() — death cleanup."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_clear_all_removes_combat_effects(self):
        """clear_all_effects should remove combat_rounds effects."""
        self.char1.apply_named_effect(
            key="stunned", duration=2, duration_type="combat_rounds",
        )
        self.char1.apply_named_effect(
            key="shield", duration=3, duration_type="combat_rounds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
        )
        self.char1.clear_all_effects()
        self.assertFalse(self.char1.has_effect("stunned"))
        self.assertFalse(self.char1.has_effect("shield"))

    def test_clear_all_removes_seconds_effects(self):
        """clear_all_effects should remove seconds-based effects."""
        self.char1.apply_named_effect(
            key="mage_armored", duration=3600, duration_type="seconds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
        )
        self.assertTrue(self.char1.has_effect("mage_armored"))
        self.char1.clear_all_effects()
        self.assertFalse(self.char1.has_effect("mage_armored"))

    def test_clear_all_removes_permanent_effects(self):
        """clear_all_effects should remove permanent (no duration) effects."""
        self.char1.apply_named_effect(
            key="offensive_stance", duration_type=None, duration=None,
            effects=[{"type": "stat_bonus", "stat": "total_hit_bonus", "value": 2}],
        )
        self.assertTrue(self.char1.has_effect("offensive_stance"))
        self.char1.clear_all_effects()
        self.assertFalse(self.char1.has_effect("offensive_stance"))

    def test_clear_all_reverses_stat_effects(self):
        """clear_all_effects should restore stats to base values."""
        original_ac = self.char1.armor_class
        original_hit = self.char1.total_hit_bonus
        self.char1.apply_named_effect(
            key="shield", duration=3, duration_type="combat_rounds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 5}],
        )
        self.char1.apply_named_effect(
            key="mage_armored", duration=3600, duration_type="seconds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
        )
        self.char1.apply_named_effect(
            key="staggered", duration=2, duration_type="combat_rounds",
            effects=[{"type": "stat_bonus", "stat": "total_hit_bonus", "value": -3}],
        )
        self.char1.clear_all_effects()
        self.assertEqual(self.char1.armor_class, original_ac)
        self.assertEqual(self.char1.total_hit_bonus, original_hit)

    def test_clear_all_removes_conditions(self):
        """clear_all_effects should remove conditions granted by named effects."""
        self.char1.apply_named_effect(
            key="slowed", condition=Condition.SLOWED,
            duration=2, duration_type="combat_rounds",
        )
        self.char1.apply_named_effect(
            key="invisible", condition=Condition.INVISIBLE,
            duration=300, duration_type="seconds",
        )
        self.assertTrue(self.char1.has_condition(Condition.SLOWED))
        self.assertTrue(self.char1.has_condition(Condition.INVISIBLE))
        self.char1.clear_all_effects()
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))
        self.assertFalse(self.char1.has_condition(Condition.INVISIBLE))

    def test_clear_all_preserves_racial_conditions(self):
        """clear_all_effects should NOT remove conditions from racial sources."""
        # Simulate racial darkvision (ref-counted, not from named effect)
        self.char1._add_condition_raw(Condition.DARKVISION)
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 1)

        # Add a named effect with a condition
        self.char1.apply_named_effect(
            key="slowed", condition=Condition.SLOWED,
            duration=2, duration_type="combat_rounds",
        )
        self.char1.clear_all_effects()

        # SLOWED from named effect gone, DARKVISION from race preserved
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))
        self.assertTrue(self.char1.has_condition(Condition.DARKVISION))
        self.assertEqual(self.char1.get_condition_count(Condition.DARKVISION), 1)

    def test_clear_all_noop_when_empty(self):
        """clear_all_effects with no active effects should be a safe no-op."""
        original_ac = self.char1.armor_class
        self.char1.clear_all_effects()
        self.assertEqual(self.char1.armor_class, original_ac)
        self.assertEqual(dict(self.char1.active_effects), {})

    def test_clear_all_is_silent(self):
        """clear_all_effects should NOT send end messages."""
        self.char1.apply_named_effect(
            key="stunned", duration=2, duration_type="combat_rounds",
            messages={"start": "Stunned!", "end": "No longer stunned."},
        )
        # Clear the msg mock's call list
        self.char1.msg = MagicMock()
        self.char1.clear_all_effects()
        # No end messages should have been sent
        for call in self.char1.msg.call_args_list:
            self.assertNotIn("No longer stunned", str(call))

    def test_clear_all_empties_active_effects_dict(self):
        """clear_all_effects should leave active_effects as empty dict."""
        self.char1.apply_named_effect(
            key="stunned", duration=2, duration_type="combat_rounds",
        )
        self.char1.apply_named_effect(
            key="shield", duration=3, duration_type="combat_rounds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
        )
        self.char1.apply_named_effect(
            key="mage_armored", duration=3600, duration_type="seconds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
        )
        self.char1.clear_all_effects()
        self.assertEqual(dict(self.char1.active_effects), {})

    def test_clear_all_mixed_durations(self):
        """clear_all_effects strips combat_rounds, seconds, and permanent together."""
        original_ac = self.char1.armor_class

        # combat_rounds effect
        self.char1.apply_named_effect(
            key="shield", duration=3, duration_type="combat_rounds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 2}],
        )
        # seconds effect
        self.char1.apply_named_effect(
            key="mage_armored", duration=3600, duration_type="seconds",
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": 4}],
        )
        # permanent effect (stance)
        self.char1.apply_named_effect(
            key="offensive_stance", duration_type=None, duration=None,
            effects=[{"type": "stat_bonus", "stat": "total_hit_bonus", "value": 3}],
        )
        # condition-only
        self.char1.apply_named_effect(
            key="slowed", condition=Condition.SLOWED,
            duration=2, duration_type="combat_rounds",
        )

        self.char1.clear_all_effects()

        self.assertEqual(dict(self.char1.active_effects), {})
        self.assertEqual(self.char1.armor_class, original_ac)
        self.assertEqual(self.char1.total_hit_bonus, 0)
        self.assertFalse(self.char1.has_condition(Condition.SLOWED))

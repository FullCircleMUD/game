"""
EffectsManagerMixin — unified effect system for all actors.

Replaces ConditionsMixin. Provides three layers:

  Layer 1 — Condition Flags (ref-counted):
    _add_condition_raw / _remove_condition_raw — silent, internal use
    add_condition / remove_condition — public API (BaseActor overrides for messaging)
    has_condition — boolean check, unchanged from ConditionsMixin

  Layer 2 — Stat Effect Dispatch (backward compatible):
    apply_effect / remove_effect — same 5 effect types as before
    Used by equipment wear_effects, potions, racial effects

  Layer 3 — Named Effects (NEW):
    apply_named_effect — tracked, timed, anti-stacking, with messaging
    remove_named_effect — symmetric reversal of everything
    has_effect — check if a named effect is active
    tick_combat_round — decrement combat_rounds effects, auto-expire
    clear_combat_effects — remove all combat_rounds effects (combat end)

Named effects compose from the three building blocks:
  A. Condition flag (optional) — set via _add_condition_raw
  B. Stat effects (optional) — dispatched via apply_effect
  C. Lifecycle (optional) — combat_rounds, seconds, or permanent

Convenience methods (preferred public API):
    # Each effect has a dedicated method — single source of truth
    target.apply_stunned(duration_rounds=1, source=attacker)
    target.apply_slowed(duration_rounds=3, source=caster)
    caster.apply_invisible(duration_seconds=300)
    caster.apply_mage_armor(ac_bonus=4, duration_seconds=3600)

    # Raw API (for data-driven callers like potions):
    target.apply_named_effect(key="potion_strength", effects=[...], duration=120)

Requires host class to also mix in DamageResistanceMixin (for damage_resistance
effect type) and define hit_bonuses/damage_bonuses AttributeProperties.

See CLAUDE.md "Effect System Framework" for the full decision tree.
"""

import time
from enum import Enum

from evennia.typeclasses.attributes import AttributeProperty

from enums.condition import Condition
from enums.named_effect import NamedEffect

# Sentinel to distinguish "caller didn't pass this kwarg" from "caller passed None".
# Used by apply_named_effect() for auto-filling condition and duration_type from
# the NamedEffect registry.
_UNSET = object()


class EffectsManagerMixin:
    """
    Unified effect management for actors.

    Replaces ConditionsMixin and absorbs apply_effect/remove_effect
    from BaseActor. Adds a named effect system with built-in
    anti-stacking and lifecycle management.
    """

    # ================================================================== #
    #  Layer 1 — Condition Flag Store (ref-counted)
    # ================================================================== #

    # Ref-counted condition flags: {"hidden": 1, "darkvision": 2}
    conditions = AttributeProperty(default={})

    # Named effects: {"shield": {...}, "stunned": {...}}
    active_effects = AttributeProperty(default={})

    def _condition_key(self, condition):
        """Accept Condition enum or raw string, return string key."""
        if isinstance(condition, Enum):
            return condition.value
        return condition

    def _add_condition_raw(self, condition):
        """
        Increment ref count for condition. Returns True if newly gained.
        No messaging — used internally by named effects.
        """
        key = self._condition_key(condition)
        conds = dict(self.conditions)
        old_count = conds.get(key, 0)
        conds[key] = old_count + 1
        self.conditions = conds
        return old_count == 0

    def _remove_condition_raw(self, condition):
        """
        Decrement ref count for condition. Returns True if fully removed.
        No messaging — used internally by named effects.
        """
        key = self._condition_key(condition)
        conds = dict(self.conditions)
        old_count = conds.get(key, 0)
        if old_count <= 0:
            return False
        new_count = old_count - 1
        if new_count == 0:
            conds.pop(key, None)
        else:
            conds[key] = new_count
        self.conditions = conds
        return new_count == 0

    def has_condition(self, condition):
        """Return True if condition is active (ref count > 0)."""
        key = self._condition_key(condition)
        return self.conditions.get(key, 0) > 0

    def get_condition_count(self, condition):
        """Return raw ref count for condition."""
        key = self._condition_key(condition)
        return self.conditions.get(key, 0)

    def add_condition(self, condition):
        """
        Public condition API — add with messaging.

        Returns True if newly gained (count was 0).
        BaseActor overrides this to add start messages + side effects.
        """
        return self._add_condition_raw(condition)

    def remove_condition(self, condition):
        """
        Public condition API — remove with messaging.

        Returns True if fully removed (count reached 0).
        BaseActor overrides this to add end messages + side effects.
        """
        return self._remove_condition_raw(condition)

    def break_effect(self, named_effect):
        """
        Force-remove a named effect: zero condition refs, reverse stats, stop timer.

        Does NOT send end messages — the caller handles context-specific messaging
        (e.g. "Your invisibility breaks as you attack!" vs "Your invisibility fades.").

        Used for break-on-action effects (invisibility breaks on attack, sanctuary
        breaks on offensive action, etc.).

        Args:
            named_effect: NamedEffect enum or string key

        Returns True if the effect was active (and is now removed).
        """
        if isinstance(named_effect, NamedEffect):
            ne = named_effect
            key = ne.value
        else:
            try:
                ne = NamedEffect(named_effect)
            except ValueError:
                return False
            key = ne.value

        # Check: the effect must be active (via condition or effect record)
        condition = ne.effect_condition
        if condition:
            if not self.has_condition(condition):
                return False
        elif not self.has_effect(key):
            return False

        # Zero condition refs entirely (nuke, not decrement)
        if condition:
            conds = dict(self.conditions)
            conds.pop(self._condition_key(condition), None)
            self.conditions = conds

        # Remove the named effect record + nuclear recalculate
        record = (self.active_effects or {}).get(key)
        has_stat_effects = False
        if record:
            has_stat_effects = bool(record.get("effects"))
            effects_dict = dict(self.active_effects)
            effects_dict.pop(key, None)
            self.active_effects = effects_dict

        # Stop timer script
        self._stop_effect_timer(key)

        # Recalculate after all state changes are done
        if has_stat_effects:
            self._recalculate_stats()

        return True

    def break_invisibility(self):
        """Break INVISIBLE on offensive action. Returns True if was invisible."""
        return self.break_effect(NamedEffect.INVISIBLE)

    def break_sanctuary(self):
        """Break SANCTUARY on offensive action. Returns True if had sanctuary."""
        return self.break_effect(NamedEffect.SANCTUARY)

    # ================================================================== #
    #  Layer 2 — Stat Effect Dispatch (backward compatible)
    # ================================================================== #

    def apply_effect(self, effect):
        """
        Apply a single effect dict to this actor.

        Supported effect types:
            {"type": "stat_bonus", "stat": "<stat_name>", "value": <int>}
            {"type": "damage_resistance", "damage_type": "<type>", "value": <int>}
            {"type": "condition", "condition": "<condition_name>"}
            {"type": "hit_bonus", "weapon_type": "<WeaponType.value>", "value": <int>}
            {"type": "damage_bonus", "weapon_type": "<WeaponType.value>", "value": <int>}
        """
        effect_type = effect.get("type")
        if effect_type == "stat_bonus":
            stat = effect["stat"]
            value = effect["value"]
            current = getattr(self, stat, None)
            if current is not None:
                setattr(self, stat, current + value)
        elif effect_type == "damage_resistance":
            self.apply_resistance_effect(effect)
        elif effect_type == "hit_bonus":
            wt = effect["weapon_type"]
            value = effect["value"]
            bonuses = dict(self.hit_bonuses)
            bonuses[wt] = bonuses.get(wt, 0) + value
            self.hit_bonuses = bonuses
        elif effect_type == "damage_bonus":
            wt = effect["weapon_type"]
            value = effect["value"]
            bonuses = dict(self.damage_bonuses)
            bonuses[wt] = bonuses.get(wt, 0) + value
            self.damage_bonuses = bonuses
        elif effect_type == "condition":
            newly_gained = self.add_condition(effect["condition"])
            # Apply companion effects only on 0→1 transition
            if newly_gained:
                for sub_effect in effect.get("effects", []):
                    self.apply_effect(sub_effect)

    def remove_effect(self, effect):
        """
        Remove a single effect dict from this actor.
        Reverses apply_effect().
        """
        effect_type = effect.get("type")
        if effect_type == "stat_bonus":
            stat = effect["stat"]
            value = effect["value"]
            current = getattr(self, stat, None)
            if current is not None:
                setattr(self, stat, current - value)
            self._check_encumbrance_consequences()
        elif effect_type == "damage_resistance":
            self.remove_resistance_effect(effect)
        elif effect_type == "hit_bonus":
            wt = effect["weapon_type"]
            value = effect["value"]
            bonuses = dict(self.hit_bonuses)
            bonuses[wt] = bonuses.get(wt, 0) - value
            if bonuses[wt] == 0:
                del bonuses[wt]
            self.hit_bonuses = bonuses
        elif effect_type == "damage_bonus":
            wt = effect["weapon_type"]
            value = effect["value"]
            bonuses = dict(self.damage_bonuses)
            bonuses[wt] = bonuses.get(wt, 0) - value
            if bonuses[wt] == 0:
                del bonuses[wt]
            self.damage_bonuses = bonuses
        elif effect_type == "condition":
            fully_removed = self.remove_condition(effect["condition"])
            # Reverse companion effects only on →0 transition
            if fully_removed:
                for sub_effect in effect.get("effects", []):
                    self.remove_effect(sub_effect)

    def _check_encumbrance_consequences(self):
        """No-op default. Overridden by classes with CarryingCapacityMixin."""
        pass

    # ================================================================== #
    #  Layer 3 — Named Effects
    # ================================================================== #

    def apply_named_effect(self, key, source=None, effects=None,
                           condition=_UNSET, duration=None,
                           duration_type=_UNSET, messages=None,
                           save_dc=None, save_stat=None, save_messages=None):
        """
        Apply a tracked, named effect with optional condition, stats, and lifecycle.

        Prefer the convenience methods (apply_stunned, apply_invisible, etc.)
        which call this internally. Use this directly only for data-driven
        callers like potions where the effect key comes from item attributes.

        Args:
            key: NamedEffect enum or string key (validated against enum)
            source: the actor/object that caused the effect (passed to on-apply callbacks)
            effects: list of effect dicts for Layer 2 dispatch
            condition: Condition enum, None, or _UNSET (auto-fill from registry)
            duration: int — rounds or seconds (None = permanent)
            duration_type: "combat_rounds", "seconds", None, or _UNSET (auto-fill)
            messages: dict with optional keys (auto-populated from NamedEffect enum if None):
                start — first-person message on application
                end — first-person message on removal
                start_third — third-person template with {name} placeholder
                end_third — third-person template with {name} placeholder
            save_dc: int — DC for save-each-round escape (None = no save)
            save_stat: str — stat name for save roll (e.g. "strength")
            save_messages: dict with optional keys:
                success — first-person message on save success ({roll}, {dc})
                fail — first-person message on save failure ({roll}, {dc})
                success_third — third-person template ({name}, {roll}, {dc})
                fail_third — third-person template ({name}, {roll}, {dc})

        Returns True if applied, False if already active (anti-stacking).
        """
        # Accept NamedEffect enum or string key
        if isinstance(key, NamedEffect):
            ne = key
            key = ne.value
        else:
            try:
                ne = NamedEffect(key)
            except ValueError:
                raise ValueError(
                    f"Unknown named effect '{key}'. "
                    f"Register it in enums/named_effect.py first."
                )

        # Auto-fill from registry when not explicitly provided
        if condition is _UNSET:
            condition = ne.effect_condition
        if duration_type is _UNSET:
            duration_type = ne.effect_duration_type

        if self.has_effect(key):
            return False

        # Auto-populate default messages from NamedEffect enum if not provided
        if messages is None:
            messages = {
                "start": ne.get_start_message(),
                "end": ne.get_end_message(),
                "start_third": ne.get_start_message_third_person("{name}"),
                "end_third": ne.get_end_message_third_person("{name}"),
            }

        # Snapshot visibility BEFORE changes for correct room messaging
        was_hidden = self.has_condition(Condition.HIDDEN)
        was_invisible = self.has_condition(Condition.INVISIBLE)

        # Record the effect
        record = {
            "condition": self._condition_key(condition) if condition else None,
            "effects": list(effects) if effects else [],
            "duration": duration,
            "duration_type": duration_type,
            "messages": dict(messages) if messages else {},
            "save_dc": save_dc,
            "save_stat": save_stat,
            "save_messages": dict(save_messages) if save_messages else {},
        }
        effects_dict = dict(self.active_effects)
        effects_dict[key] = record
        self.active_effects = effects_dict

        # A: condition flag (raw — no messaging, we handle it below)
        if condition:
            self._add_condition_raw(condition)

        # B: stat effects — nuclear recalculate
        if record["effects"]:
            self._recalculate_stats()

        # Messaging
        msgs = record["messages"]
        start_msg = msgs.get("start")
        if start_msg:
            self.msg(start_msg)
        start_third = msgs.get("start_third")
        if start_third and getattr(self, "location", None):
            if not was_hidden:
                from_obj = self if was_invisible else None
                self.location.msg_contents(
                    start_third.format(name=self.key),
                    exclude=[self],
                    from_obj=from_obj,
                )

        # C: lifecycle
        if duration_type == "seconds" and duration:
            self._start_effect_timer(key, duration)
        # combat_rounds: handled by tick_combat_round()

        # D: registered side-effect callbacks (e.g. prone → advantage to enemies)
        from enums.named_effect import get_on_apply_callback
        callback = get_on_apply_callback(key)
        if callback:
            callback(target=self, source=source, duration=duration)

        return True

    def remove_named_effect(self, key):
        """
        Remove a named effect, reversing all its components.

        Reverses stat effects, clears condition flag, sends end messages,
        cleans up timer scripts.

        Returns True if removed, False if not found.
        """
        effects_dict = dict(self.active_effects)
        record = effects_dict.pop(key, None)
        if not record:
            return False
        self.active_effects = effects_dict

        # Reverse B: stat effects — nuclear recalculate
        has_stat_effects = bool(record.get("effects"))

        # Reverse A: condition flag
        condition_key = record.get("condition")
        if condition_key:
            self._remove_condition_raw(condition_key)

        # Messaging (check visibility AFTER removal for correct filtering)
        msgs = record.get("messages", {})
        end_msg = msgs.get("end")
        if end_msg:
            self.msg(end_msg)
        end_third = msgs.get("end_third")
        if end_third and getattr(self, "location", None):
            if not self.has_condition(Condition.HIDDEN):
                from_obj = self if self.has_condition(Condition.INVISIBLE) else None
                self.location.msg_contents(
                    end_third.format(name=self.key),
                    exclude=[self],
                    from_obj=from_obj,
                )

        # Cleanup timer if seconds-based
        if record.get("duration_type") == "seconds":
            self._stop_effect_timer(key)

        # Nuclear recalculate after all condition/messaging is done
        if has_stat_effects:
            self._recalculate_stats()

        return True

    def has_effect(self, key):
        """Check if a named effect is currently active."""
        return key in (self.active_effects or {})

    def get_named_effect(self, key):
        """Get the record for a named effect, or None if not active."""
        return (self.active_effects or {}).get(key)

    def get_effect_remaining_seconds(self, key):
        """
        Return remaining seconds for a seconds-based effect, or None.

        Uses the start_time stored on the timer script to calculate elapsed
        time, then subtracts from the original duration.
        """
        record = self.get_named_effect(key)
        if not record or record.get("duration_type") != "seconds":
            return None
        scripts = self.scripts.get(f"effect_timer_{key}")
        if not scripts:
            return None
        start_time = scripts[0].db.start_time
        if start_time is None:
            return None
        elapsed = time.time() - start_time
        return max(0, record.get("duration", 0) - elapsed)

    # ================================================================== #
    #  Lifecycle — Combat Round Ticking
    # ================================================================== #

    def tick_combat_round(self):
        """
        Decrement all combat_rounds effects by 1. Auto-remove expired ones.
        For effects with save_dc, roll a save first — success = immediate removal.
        Called by combat handler each tick.
        """
        from utils.dice_roller import dice

        effects_dict = dict(self.active_effects)
        expired = []
        for key, record in effects_dict.items():
            if (record.get("duration_type") == "combat_rounds"
                    and record.get("duration") is not None):
                # Save-each-round check (e.g. bola entangle)
                save_dc = record.get("save_dc")
                if save_dc is not None:
                    save_stat = record.get("save_stat", "strength")
                    stat_value = getattr(self, save_stat, 10)
                    stat_bonus = self.get_attribute_bonus(stat_value)
                    save_roll = dice.roll("1d20") + stat_bonus + getattr(self, "save_bonus", 0)
                    save_msgs = record.get("save_messages", {})
                    if save_roll >= save_dc:
                        # Save succeeded — break free
                        msg = save_msgs.get("success", "")
                        if msg:
                            self.msg(msg.format(roll=save_roll, dc=save_dc))
                        third = save_msgs.get("success_third", "")
                        if third and getattr(self, "location", None):
                            self.location.msg_contents(
                                third.format(name=self.key, roll=save_roll, dc=save_dc),
                                exclude=[self],
                            )
                        expired.append(key)
                        continue
                    else:
                        # Save failed — still trapped
                        msg = save_msgs.get("fail", "")
                        if msg:
                            self.msg(msg.format(roll=save_roll, dc=save_dc))
                        third = save_msgs.get("fail_third", "")
                        if third and getattr(self, "location", None):
                            self.location.msg_contents(
                                third.format(name=self.key, roll=save_roll, dc=save_dc),
                                exclude=[self],
                            )

                # Copy the record to avoid mutating _SaverDict internals
                updated = dict(record)
                updated["duration"] -= 1
                effects_dict[key] = updated
                if updated["duration"] <= 0:
                    expired.append(key)
        self.active_effects = effects_dict

        # Remove expired effects (handles stat reversal + messaging)
        for key in expired:
            self.remove_named_effect(key)

    def clear_combat_effects(self):
        """
        Remove all combat_rounds effects. Called on combat end.
        Ensures no combat-bound state persists after combat.
        """
        effects_dict = dict(self.active_effects)
        combat_keys = [
            k for k, v in effects_dict.items()
            if v.get("duration_type") == "combat_rounds"
        ]
        for key in combat_keys:
            self.remove_named_effect(key)

    # Known companion scripts for named effects (DoT scripts, external timers)
    _EFFECT_COMPANION_SCRIPTS = {
        "poisoned": "poison_dot",
        "acid_arrow": "acid_dot",
        "vampiric": "vampiric_timer",
    }

    def clear_all_effects(self):
        """
        Strip ALL named effects — seconds-based, combat_rounds, and permanent.

        Silent — no end messages. Used on death where the death announcement
        provides all context. Stops all timer scripts and companion DoT scripts,
        clears conditions contributed by named effects, and rebuilds stats
        with a single recalculate.

        Racial conditions (darkvision, etc.) are unaffected — they are
        ref-counted separately, not stored as named effects.
        """
        effects_dict = dict(self.active_effects)
        if not effects_dict:
            return

        has_stat_effects = False
        for key, record in effects_dict.items():
            # Decrement condition ref
            condition_key = record.get("condition")
            if condition_key:
                self._remove_condition_raw(condition_key)

            if record.get("effects"):
                has_stat_effects = True

            # Stop standard timer scripts (effect_timer_{key})
            self._stop_effect_timer(key)

            # Stop companion DoT/timer scripts
            companion_key = self._EFFECT_COMPANION_SCRIPTS.get(key)
            if companion_key:
                scripts = self.scripts.get(companion_key)
                if scripts:
                    scripts[0].delete()

        # Clear all active effects at once
        self.active_effects = {}

        # Single recalculate after everything is cleared
        if has_stat_effects:
            self._recalculate_stats()

    # ================================================================== #
    #  Lifecycle — Seconds-Based Timer Scripts
    # ================================================================== #

    def _start_effect_timer(self, key, duration_seconds):
        """Create a one-shot timer script for seconds-based effects."""
        from evennia.utils.create import create_script
        from typeclasses.scripts.effect_timer import EffectTimerScript

        script = create_script(
            EffectTimerScript,
            obj=self,
            key=f"effect_timer_{key}",
            autostart=False,
        )
        script.db.effect_key = key
        script.db.start_time = time.time()
        script.interval = duration_seconds
        script.start()

    def _stop_effect_timer(self, key):
        """Stop and remove a timer script for an effect."""
        scripts = self.scripts.get(f"effect_timer_{key}")
        if scripts:
            scripts[0].delete()

    # ================================================================== #
    #  Convenience Methods — Single Source of Truth Per Effect
    # ================================================================== #
    #
    # These are the PREFERRED public API for applying effects. Each method
    # encapsulates the correct condition, duration_type, messages, and
    # effect structure for its effect. Callers only pass what varies
    # (duration, stat values, source).
    #
    # For data-driven callers (potions), use apply_named_effect() directly
    # — it auto-fills condition and duration_type from the registry.
    # ================================================================== #

    # --- Combat Condition Effects (combat_rounds) --- #

    def apply_stunned(self, duration_rounds, source=None):
        """Apply STUNNED for N combat rounds."""
        return self.apply_named_effect(
            NamedEffect.STUNNED, duration=duration_rounds, source=source,
        )

    def apply_prone(self, duration_rounds, source=None):
        """Apply PRONE for N combat rounds."""
        return self.apply_named_effect(
            NamedEffect.PRONE, duration=duration_rounds, source=source,
        )

    def apply_slowed(self, duration_rounds, source=None):
        """Apply SLOWED for N combat rounds (sets Condition.SLOWED via registry)."""
        return self.apply_named_effect(
            NamedEffect.SLOWED, duration=duration_rounds, source=source,
        )

    def apply_paralysed(self, duration_rounds, source=None, save_dc=None,
                        save_stat="wisdom", save_messages=None, messages=None):
        """Apply PARALYSED for N combat rounds (sets Condition.PARALYSED via registry)."""
        return self.apply_named_effect(
            NamedEffect.PARALYSED, duration=duration_rounds, source=source,
            save_dc=save_dc, save_stat=save_stat, save_messages=save_messages,
            messages=messages,
        )

    def apply_entangled(self, duration_rounds, source=None, save_dc=None,
                        save_stat="strength", save_messages=None, messages=None):
        """Apply ENTANGLED with optional save-each-round escape."""
        return self.apply_named_effect(
            NamedEffect.ENTANGLED, duration=duration_rounds, source=source,
            save_dc=save_dc, save_stat=save_stat, save_messages=save_messages,
            messages=messages,
        )

    def apply_blurred(self, duration_rounds):
        """Apply BLURRED for N combat rounds."""
        return self.apply_named_effect(
            NamedEffect.BLURRED, duration=duration_rounds,
        )

    # --- Combat Stat Effects (combat_rounds) --- #

    def apply_shield_buff(self, ac_bonus, duration_rounds, mana_cost=0):
        """Apply Shield reactive AC buff for N combat rounds."""
        round_s = "round" if duration_rounds == 1 else "rounds"
        mana_part = f", {mana_cost} mana" if mana_cost else ""
        ne = NamedEffect.SHIELD
        return self.apply_named_effect(
            ne,
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": ac_bonus}],
            duration=duration_rounds,
            messages={
                "start": (
                    f"|C|h*SHIELD* A shimmering barrier of magical force "
                    f"springs into existence around you! (+{ac_bonus} AC, "
                    f"{duration_rounds} {round_s}{mana_part})|n"
                ),
                "end": ne.get_end_message(),
                "start_third": ne.get_start_message_third_person("{name}"),
                "end_third": ne.get_end_message_third_person("{name}"),
            },
        )

    def apply_staggered(self, hit_penalty, duration_rounds, source=None):
        """Apply STAGGERED (hit penalty) for N combat rounds."""
        return self.apply_named_effect(
            NamedEffect.STAGGERED, source=source,
            effects=[{"type": "stat_bonus", "stat": "total_hit_bonus", "value": hit_penalty}],
            duration=duration_rounds,
        )

    def apply_sundered(self, ac_penalty, duration_rounds, source=None):
        """Apply SUNDERED (AC penalty) for N combat rounds."""
        return self.apply_named_effect(
            NamedEffect.SUNDERED, source=source,
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": ac_penalty}],
            duration=duration_rounds,
        )

    # --- Seconds-Based Buffs --- #

    def apply_invisible(self, duration_seconds):
        """Apply INVISIBLE for N seconds (sets Condition.INVISIBLE via registry)."""
        return self.apply_named_effect(
            NamedEffect.INVISIBLE, duration=duration_seconds,
        )

    def apply_sanctuary(self, duration_seconds):
        """Apply SANCTUARY for N seconds (sets Condition.SANCTUARY via registry)."""
        return self.apply_named_effect(
            NamedEffect.SANCTUARY, duration=duration_seconds,
        )

    def apply_armor_buff(self, ac_bonus, duration_seconds):
        """Apply armor AC buff for N seconds (shared by Mage Armor + Divine Armor)."""
        return self.apply_named_effect(
            NamedEffect.ARMORED,
            effects=[{"type": "stat_bonus", "stat": "armor_class", "value": ac_bonus}],
            duration=duration_seconds,
        )

    # Backward-compat alias
    apply_mage_armor = apply_armor_buff

    def apply_shadowcloaked(self, stealth_bonus, duration_seconds, source=None):
        """Apply Shadowcloak stealth buff for N seconds."""
        return self.apply_named_effect(
            NamedEffect.SHADOWCLOAKED, source=source,
            effects=[{"type": "stat_bonus", "stat": "stealth_bonus", "value": stealth_bonus}],
            duration=duration_seconds,
        )

    def apply_blessed(self, hit_bonus, save_bonus, duration_seconds):
        """Apply Bless buff for N seconds (hit + save bonus)."""
        return self.apply_named_effect(
            NamedEffect.BLESSED,
            effects=[
                {"type": "stat_bonus", "stat": "total_hit_bonus", "value": hit_bonus},
                {"type": "stat_bonus", "stat": "save_bonus", "value": save_bonus},
            ],
            duration=duration_seconds,
        )

    def apply_blinded(self, duration_rounds, source=None, save_dc=None,
                      save_stat="constitution", save_messages=None, messages=None):
        """Apply BLINDED with optional save-each-round escape."""
        return self.apply_named_effect(
            NamedEffect.BLINDED, duration=duration_rounds, source=source,
            save_dc=save_dc, save_stat=save_stat, save_messages=save_messages,
            messages=messages,
        )

    def apply_water_breathing_buff(self, duration_seconds):
        """Apply Water Breathing buff for N seconds."""
        return self.apply_named_effect(
            NamedEffect.WATER_BREATHING_BUFF,
            condition=Condition.WATER_BREATHING,
            duration=duration_seconds,
        )

    def apply_darkvision_buff(self, duration_seconds):
        """Apply Darkvision buff for N seconds (shared by Darkvision + Divine Sight)."""
        return self.apply_named_effect(
            NamedEffect.DARKVISION_BUFF,
            condition=Condition.DARKVISION,
            duration=duration_seconds,
        )

    def apply_true_sight(self, duration_seconds, detect_invis=False):
        """Apply True Sight for N seconds. detect_invis adds DETECT_INVIS condition."""
        condition = Condition.DETECT_INVIS if detect_invis else None
        return self.apply_named_effect(
            NamedEffect.TRUE_SIGHT, condition=condition, duration=duration_seconds,
        )

    def apply_holy_sight(self, duration_seconds, detect_invis=False):
        """Apply Holy Sight for N seconds. detect_invis adds DETECT_INVIS condition."""
        condition = Condition.DETECT_INVIS if detect_invis else None
        return self.apply_named_effect(
            NamedEffect.HOLY_SIGHT, condition=condition, duration=duration_seconds,
        )

    def apply_resist_element(self, element, resistance_pct, duration_seconds, source=None):
        """Apply elemental resistance for N seconds.

        Args:
            element: "fire", "cold", "lightning", "acid", or "poison"
            resistance_pct: percentage resistance (e.g. 20 for 20%)
        """
        _element_effects = {
            "fire": NamedEffect.RESIST_FIRE,
            "cold": NamedEffect.RESIST_COLD,
            "lightning": NamedEffect.RESIST_LIGHTNING,
            "acid": NamedEffect.RESIST_ACID,
            "poison": NamedEffect.RESIST_POISON,
        }
        ne = _element_effects.get(element)
        if not ne:
            raise ValueError(f"Unknown element '{element}'. "
                             f"Valid: {', '.join(_element_effects)}")
        return self.apply_named_effect(
            ne, source=source,
            effects=[{"type": "damage_resistance", "damage_type": element, "value": resistance_pct}],
            duration=duration_seconds,
        )

    # --- Script-Managed Effects --- #

    def apply_poisoned(self, ticks):
        """Apply POISONED marker (lifecycle managed by PoisonDoTScript)."""
        return self.apply_named_effect(
            NamedEffect.POISONED, duration=ticks,
        )

    def apply_acid_arrow_dot(self, dot_rounds):
        """Apply ACID_ARROW marker (lifecycle managed by AcidDoTScript)."""
        return self.apply_named_effect(
            NamedEffect.ACID_ARROW, duration=dot_rounds,
        )

    def apply_vampiric(self, source=None):
        """Apply VAMPIRIC marker (lifecycle managed by VampiricTimerScript)."""
        return self.apply_named_effect(
            NamedEffect.VAMPIRIC, source=source,
        )

    # --- Stance Effects --- #

    def apply_offensive_stance(self, effects, source=None):
        """Apply OFFENSIVE_STANCE with the given stat effects."""
        return self.apply_named_effect(
            NamedEffect.OFFENSIVE_STANCE, effects=effects, source=source,
        )

    def apply_defensive_stance(self, effects, source=None):
        """Apply DEFENSIVE_STANCE with the given stat effects."""
        return self.apply_named_effect(
            NamedEffect.DEFENSIVE_STANCE, effects=effects, source=source,
        )

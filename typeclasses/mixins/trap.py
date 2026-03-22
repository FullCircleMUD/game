"""
TrapMixin — adds trap state, detection, triggering, and disarming to any object.

Objects with this mixin can be trapped (doors, chests, exits, rooms). Traps
are detected via the search command or passive perception, and disarmed via
the SUBTERFUGE skill. Failed disarm attempts trigger the trap.

Trap payloads include damage (dice expression + damage type), named effects
(poisoned, stunned, etc.), and alarms (aggro mobs in room).

Usage (build script / prototype):
    chest.is_trapped = True
    chest.trap_armed = True
    chest.trap_find_dc = 18
    chest.trap_disarm_dc = 15
    chest.trap_damage_dice = "2d6"
    chest.trap_damage_type = "fire"
    chest.trap_effect_key = "stunned"
    chest.trap_effect_duration = 2
    chest.trap_effect_duration_type = "combat_rounds"
    chest.trap_description = "a fire trap"
"""

from evennia import AttributeProperty


class TrapMixin:
    """
    Mixin for objects that can be trapped.

    Defaults to not trapped (is_trapped=False). Configure per-instance
    to enable. Subclasses wire trigger points (open, traverse, enter).
    """

    # ── State ──
    is_trapped = AttributeProperty(False)
    trap_armed = AttributeProperty(True)
    trap_detected = AttributeProperty(False)

    # ── DCs ──
    trap_find_dc = AttributeProperty(15)
    trap_disarm_dc = AttributeProperty(15)

    # ── Behaviour ──
    trap_one_shot = AttributeProperty(True)
    trap_reset_seconds = AttributeProperty(0)  # 0 = no auto-reset

    # ── Damage payload ──
    trap_damage_dice = AttributeProperty("")      # e.g. "2d6"
    trap_damage_type = AttributeProperty(None)    # DamageType value string

    # ── Named effect payload ──
    trap_effect_key = AttributeProperty(None)     # NamedEffect key string
    trap_effect_duration = AttributeProperty(0)
    trap_effect_duration_type = AttributeProperty("seconds")

    # ── Alarm payload ──
    trap_is_alarm = AttributeProperty(False)

    # ── Description ──
    trap_description = AttributeProperty("a trap")

    # ── Initialisation ──

    def at_trap_init(self):
        """Initialize trap state. Call from at_object_creation()."""
        pass  # defaults set via AttributeProperty

    # ── Visibility ──

    def is_trap_visible_to(self, character):
        """
        Check if character can see the trap.

        A trap is visible if it exists and is detected (globally) or
        is disarmed (wreckage visible). Returns False if there is no
        trap at all.
        """
        if not self.is_trapped:
            return False
        if not self.trap_armed:
            return True  # disarmed traps are visible wreckage
        return self.trap_detected

    # ── Detection ──

    def detect_trap(self, finder):
        """
        Mark trap as globally detected. Broadcasts discovery to room.

        Args:
            finder: The character who discovered the trap.
        """
        self.trap_detected = True
        desc = self.trap_description

        # Determine target name for messaging
        from typeclasses.terrain.rooms.room_base import RoomBase
        if isinstance(self, RoomBase):
            target_str = ""
        else:
            target_str = f" on {self.key}"

        finder.msg(f"|rYou notice {desc}{target_str}!|n")

        room = self._get_trap_room()
        if room:
            room.msg_contents(
                f"$You() $conj(discover) {desc}{target_str}!",
                from_obj=finder,
                exclude=[finder],
            )

    # ── Triggering ──

    def trigger_trap(self, victim, room=None):
        """
        Fire the trap's payload on victim.

        Applies damage, named effects, and alarm. Handles one-shot
        disarming and reset timers.

        Args:
            victim: The character taking the trap effects.
            room: Override room for messaging. Defaults to self.location
                  or victim.location.
        """
        if not self.is_trapped or not self.trap_armed:
            return

        from utils.dice_roller import dice

        room = room or self._get_trap_room() or getattr(victim, "location", None)
        desc = self.trap_description
        messages = []

        # ── Damage ──
        damage_dealt = 0
        if self.trap_damage_dice:
            raw = dice.roll(self.trap_damage_dice)
            damage_dealt = victim.take_damage(
                raw,
                damage_type=self.trap_damage_type,
                cause="trap",
            )
            dtype = self.trap_damage_type or "untyped"
            messages.append(f"{damage_dealt} {dtype} damage")

        # ── Named effect ──
        if self.trap_effect_key:
            victim.apply_named_effect(
                key=self.trap_effect_key,
                duration=self.trap_effect_duration,
                duration_type=self.trap_effect_duration_type,
            )
            messages.append(self.trap_effect_key)

        # ── Messaging ──
        effect_str = " and ".join(messages) if messages else "nothing"
        victim.msg(
            f"|r{desc.capitalize()} springs! "
            f"You take {effect_str}!|n"
        )
        if room:
            room.msg_contents(
                f"|r{desc.capitalize()} springs on "
                f"$You()! ({effect_str})|n",
                from_obj=victim,
                exclude=[victim],
            )

        # ── Alarm ──
        if self.trap_is_alarm and room:
            self._trigger_alarm(victim, room)

        # ── One-shot ──
        if self.trap_one_shot:
            self.trap_armed = False

        # ── Reset timer ──
        if self.trap_reset_seconds > 0:
            self._start_trap_reset_timer()

        # ── Hook ──
        self.at_trap_trigger(victim)

    def at_trap_trigger(self, victim):
        """Hook called after trap triggers. Override for custom behaviour."""
        pass

    # ── Disarming ──

    def disarm_trap(self, character):
        """
        Attempt to disarm the trap using SUBTERFUGE skill.

        Skill bonus = mastery bonus + DEX modifier.
        Called by the disarm skill command.

        Returns:
            (bool, str): Success flag and message.
        """
        if not self.is_trapped:
            return False, "There is no trap here."

        if not self.trap_armed:
            return False, "The trap is already disarmed."

        if not self.trap_detected:
            return False, "You don't see a trap to disarm."

        from enums.mastery_level import MasteryLevel
        from enums.skills_enum import skills

        # Look up SUBTERFUGE mastery from class skills
        class_mastery = (
            getattr(character.db, "class_skill_mastery_levels", None) or {}
        )
        mastery_entry = class_mastery.get(skills.SUBTERFUGE.value)
        if mastery_entry:
            if hasattr(mastery_entry, "get"):
                mastery_int = int(mastery_entry.get("mastery", 0))
            else:
                mastery_int = int(mastery_entry)
        else:
            mastery_int = 0

        if mastery_int <= 0:
            return False, "You don't have the skill to disarm traps."

        mastery_bonus = MasteryLevel(mastery_int).bonus

        # Add DEX modifier
        dex_mod = 0
        if hasattr(character, "dexterity") and hasattr(
            character, "get_attribute_bonus"
        ):
            dex_mod = character.get_attribute_bonus(character.dexterity)

        skill_bonus = mastery_bonus + dex_mod

        # d20 + skill bonus vs trap_disarm_dc
        from utils.dice_roller import dice

        has_adv = getattr(character.db, "non_combat_advantage", False)
        has_dis = getattr(character.db, "non_combat_disadvantage", False)
        roll = dice.roll_with_advantage_or_disadvantage(
            advantage=has_adv, disadvantage=has_dis
        )
        character.db.non_combat_advantage = False
        character.db.non_combat_disadvantage = False
        total = roll + skill_bonus

        if total >= self.trap_disarm_dc:
            self.trap_armed = False
            self.at_trap_disarm(character)
            return True, (
                f"You carefully disarm {self.trap_description}. "
                f"(Roll: {roll} + {skill_bonus} = {total} "
                f"vs DC {self.trap_disarm_dc})"
            )
        else:
            # Failed disarm triggers the trap
            self.trigger_trap(character)
            return False, (
                f"You fumble the disarm and trigger {self.trap_description}! "
                f"(Roll: {roll} + {skill_bonus} = {total} "
                f"vs DC {self.trap_disarm_dc})"
            )

    def at_trap_disarm(self, character):
        """Hook called after successful disarm. Override for custom behaviour."""
        pass

    # ── Internal helpers ──

    def _get_trap_room(self):
        """Get the room this trap is in (works for objects, exits, and rooms)."""
        from typeclasses.terrain.rooms.room_base import RoomBase
        if isinstance(self, RoomBase):
            return self
        return getattr(self, "location", None)

    def _trigger_alarm(self, victim, room):
        """Alert CombatMobs in the room about the trap trigger."""
        for obj in room.contents:
            if obj == victim:
                continue
            if hasattr(obj, "at_new_arrival"):
                obj.at_new_arrival(victim)
        if room:
            room.msg_contents(
                f"|yAn alarm sounds from {self.trap_description}!|n"
            )

    def _start_trap_reset_timer(self):
        """Start a TrapResetScript if trap_reset_seconds > 0."""
        if not self.trap_reset_seconds or self.trap_reset_seconds <= 0:
            return

        from typeclasses.scripts.trap_reset_timer import TrapResetScript

        # Remove any existing reset timer
        self.scripts.delete("trap_reset_timer")

        script = self.scripts.add(
            TrapResetScript,
            autostart=False,
        )
        script.db.reset_seconds = self.trap_reset_seconds
        script.interval = self.trap_reset_seconds
        script.start()

"""
AggressiveMixin — composable aggression behavior for mobs.

Provides the common aggro pattern: attack players on sight, scan for
targets during AI wander ticks, and match height to reach targets.

Requires the host class to provide:
  - is_alive (AttributeProperty)
  - is_low_health (property, from CombatMixin)
  - initiate_attack(target) (from CombatMixin)
  - attack_delay_min, attack_delay_max (AttributeProperties)
  - room_vertical_position (from BaseActor)
  - has_condition() (from EffectsManagerMixin)
  - ai (lazy_property, from StateMachineAIMixin)
  - wander() (method, from CombatMob)
"""

import random

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from combat.height_utils import can_reach_target
from enums.condition import Condition


class AggressiveMixin:
    """Mixin providing aggression behavior — attacks players on sight."""

    is_aggressive_to_players = AttributeProperty(True)

    def at_new_arrival(self, arriving_obj):
        """Aggro on players when healthy and reachable."""
        if not self.is_alive or arriving_obj == self:
            return
        if self.is_low_health:
            return
        if getattr(arriving_obj, "is_pc", False):
            self._try_reach_and_attack(arriving_obj)

    def _try_reach_and_attack(self, target):
        """Adjust height if possible, then schedule attack if reachable."""
        weapon = self.get_slot("WIELD") if hasattr(self, "get_slot") else None
        if not can_reach_target(self, target, weapon):
            # Try to match target's height
            if self._try_match_height(target):
                self._schedule_attack(target)
            # else: can't reach, don't aggro
        else:
            self._schedule_attack(target)

    def _try_match_height(self, target):
        """
        Try to change vertical position to match target's height.

        Returns True if height was successfully matched, False otherwise.
        Flying mobs can ascend/descend, swimming mobs can dive/surface.
        """
        target_height = target.room_vertical_position
        my_height = self.room_vertical_position
        if target_height == my_height:
            return True

        room = self.location
        if not room:
            return False

        if target_height > my_height:
            # Target is above — need FLY condition
            if not self.has_condition(Condition.FLY):
                return False
            max_height = getattr(room, "max_height", 0)
            if target_height > max_height:
                return False
            self.room_vertical_position = target_height
            return True

        if target_height < my_height:
            if target_height < 0:
                # Target is underwater — need WATER_BREATHING
                if not self.has_condition(Condition.WATER_BREATHING):
                    return False
                max_depth = getattr(room, "max_depth", 0)
                if target_height < max_depth:
                    return False
            # Descending from flight to ground/underwater — just set position
            self.room_vertical_position = target_height
            return True

        return False

    def _schedule_attack(self, target):
        """Schedule an attack after a random delay."""
        attack_delay = random.uniform(
            self.attack_delay_min, self.attack_delay_max
        )
        delay(attack_delay, self._execute_attack, target)

    def _execute_attack(self, target):
        """Start combat if target is still valid."""
        if not self.is_alive or not self.location:
            return
        if self.is_low_health:
            return
        if getattr(target, "hp", 0) <= 0 or target.location != self.location:
            return
        # Re-check reachability (target may have moved height during delay)
        weapon = self.get_slot("WIELD") if hasattr(self, "get_slot") else None
        if not can_reach_target(self, target, weapon):
            if not self._try_match_height(target):
                return
        self.initiate_attack(target)

    def ai_wander(self):
        """Scan for players, attack if found, otherwise wander."""
        if not self.location:
            return
        if self.is_low_health:
            self.ai.set_state("retreating")
            return
        if self.scripts.get("combat_handler"):
            return

        players = self.ai.get_targets_in_room()
        if players:
            # Prefer reachable targets, but try height-matching for others
            target = random.choice(players)
            self._try_reach_and_attack(target)
            return

        if random.random() < 0.25:
            self.wander()

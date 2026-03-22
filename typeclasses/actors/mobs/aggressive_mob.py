"""
AggressiveMob — CombatMob that attacks players on sight.

Provides the common aggro pattern used by wolves, dire wolves, cellar rats,
sewer rats, and any future mob that should attack players automatically:
  - at_new_arrival(): schedule attack when a player enters the room
  - ai_wander(): scan for players each tick, wander if none found
  - _schedule_attack() / _execute_attack(): delayed attack with validation

Subclasses override to add extra behavior (rabbit hunting, dodge, etc.).
Prototype mobs (e.g. sewer rats) can use this typeclass directly via
ZoneSpawnScript JSON configs with attrs overrides.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from typeclasses.actors.mob import CombatMob


class AggressiveMob(CombatMob):
    """CombatMob that attacks players on sight with a random delay."""

    is_aggressive_to_players = AttributeProperty(True)

    def at_new_arrival(self, arriving_obj):
        """Aggro on players when healthy."""
        if not self.is_alive or arriving_obj == self:
            return
        if self.is_low_health:
            return
        if getattr(arriving_obj, "is_pc", False):
            self._schedule_attack(arriving_obj)

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
        if not target.is_alive or target.location != self.location:
            return
        self.mob_attack(target)

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
            self._schedule_attack(random.choice(players))
            return

        if random.random() < 0.25:
            self.wander()

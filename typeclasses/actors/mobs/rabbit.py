"""
Rabbit — timid animal mob that flees from everything.

Wanders the woods at random intervals. When a character, wolf, or dire
wolf enters the room, the rabbit flees 4-5 seconds later. If the new
room also has threats, it flees again.

No combat abilities — purely prey.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from typeclasses.actors.mob import CombatMob


class Rabbit(CombatMob):
    """A small rabbit that wanders and flees from threats."""

    # ── Stats — tiny and fragile ──
    hp = AttributeProperty(3)
    hp_max = AttributeProperty(3)
    strength = AttributeProperty(3)
    dexterity = AttributeProperty(14)
    constitution = AttributeProperty(3)
    base_armor_class = AttributeProperty(12)
    armor_class = AttributeProperty(12)
    level = AttributeProperty(1)

    # ── Gold loot ──
    loot_gold_max = AttributeProperty(1)

    # ── Combat ──
    initiative_speed = AttributeProperty(4)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)
    respawn_delay = AttributeProperty(30)

    def at_new_arrival(self, arriving_obj):
        """Something entered the room — schedule flee if it's a threat."""
        if not self.is_alive or arriving_obj == self:
            return

        if self._is_threat(arriving_obj):
            delay(
                random.uniform(4, 5),
                self._flee_reaction,
            )

    def _is_threat(self, obj):
        """Return True if obj is something the rabbit should flee from."""
        if getattr(obj, "is_pc", False):
            return True
        # Flee from wolves/dire wolves but not other rabbits
        if isinstance(obj, CombatMob) and not isinstance(obj, Rabbit):
            return True
        return False

    def _flee_reaction(self):
        """Execute the flee — move to an adjacent room if threats remain."""
        if not self.is_alive or not self.location:
            return

        # In combat the combat handler drives behaviour — don't bypass it
        if self.scripts.get("combat_handler"):
            return

        threats = [
            obj for obj in self.location.contents
            if obj != self and self._is_threat(obj)
        ]
        if not threats:
            return

        self.location.msg_contents(
            "A rabbit bolts away in fright!",
            from_obj=self, exclude=[self],
        )
        self.flee_to_random_room()

    # ── AI States ──

    def ai_wander(self):
        """Wander slowly through the woods. Flee if in combat."""
        if not self.location:
            return

        # In combat — always try to flee
        if self.scripts.get("combat_handler"):
            self.execute_cmd("flee")
            return

        # Check for threats — if any, schedule flee
        threats = [
            obj for obj in self.location.contents
            if obj != self and self._is_threat(obj)
        ]
        if threats:
            delay(
                random.uniform(4, 5),
                self._flee_reaction,
            )
            return

        # Random movement
        if random.random() < 0.2:
            self.wander()

"""
Rabbit — skittish prey that flees on sight but fights when cornered.

Behavioural opposite of Mouse: when a character/wolf/dire-wolf enters
the room, the rabbit flees 4-5 seconds later. If caught and attacked,
it stands and fights for its 7 HP rather than fleeing combat.

Three indistinguishable variants share the same key/desc:
- Rabbit — carries 1 gold
- RabbitRich — carries 2 gold
- RabbitFat — carries 1 animal fat, no gold
"""

import random

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from enums.size import Size
from typeclasses.actors.mob import CombatMob


class Rabbit(CombatMob):
    """A small rabbit that wanders and flees from threats."""

    base_size = AttributeProperty(Size.TINY.value)
    size = AttributeProperty(Size.TINY.value)
    room_description = AttributeProperty(
        "nibbles warily at the grass, long ears twitching at every sound."
    )

    # ── Stats — small but bites back when cornered ──
    hp = AttributeProperty(7)
    base_hp_max = AttributeProperty(7)
    hp_max = AttributeProperty(7)
    base_strength = AttributeProperty(4)
    strength = AttributeProperty(4)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(5)
    constitution = AttributeProperty(5)
    base_armor_class = AttributeProperty(12)
    armor_class = AttributeProperty(12)
    level = AttributeProperty(2)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("nips at")

    # ── Loot — base variant carries 1 gold ──
    loot_gold_max = AttributeProperty(1)

    # ── XP override ──
    xp_award = AttributeProperty(15)

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
        """Wander slowly through the fields. Stand and fight if in combat."""
        if not self.location:
            return

        # In combat — let the combat handler drive (rabbit fights back, doesn't flee)
        if self.scripts.get("combat_handler"):
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


class RabbitRich(Rabbit):
    """Rabbit variant — carries 2 gold."""

    loot_gold_max = AttributeProperty(2)


class RabbitFat(Rabbit):
    """Rabbit variant — carries 1 animal fat instead of gold."""

    loot_gold_max = AttributeProperty(0)
    loot_resources = AttributeProperty({45: 1})  # 1 animal fat

"""
Rabbit — skittish prey that flees on sight but fights when cornered.

Behavioural opposite of Mouse: when a player character or an aggressive
mob enters the room, the rabbit flees 2-3 seconds later. If caught and
attacked, it stands and fights for its 7 HP rather than fleeing combat.

Three indistinguishable variants share the same key/desc:
- Rabbit — carries 1 gold
- RabbitRich — carries 2 gold
- RabbitFat — carries 1 animal fat, no gold
"""

import random

from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import delay

from enums.size import Size
from typeclasses.actors.character import FCMCharacter
from typeclasses.actors.mob import CombatMob
from typeclasses.mixins.aggressive_mixin import AggressiveMixin
from utils.targeting.predicates import p_is_typeclass


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

    # ── Loot lives in YAML (mob-spawner rules) ──

    # ── XP override ──
    xp_award = AttributeProperty(15)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)

    def at_new_arrival(self, arriving_obj):
        """Something entered the room — schedule flee if it's a threat."""
        if not self.is_alive or arriving_obj == self:
            return

        if all(p(arriving_obj, self) for p in THREAT_PREDICATES):
            delay(
                random.uniform(2, 3),
                self._flee_reaction,
            )

    def _flee_reaction(self):
        """
        Execute the flee — move to an adjacent room if threats remain.

        Both callers check for a threat before scheduling this, but they
        schedule it on a 2-3 second delay, so the check runs again here.
        The threat may have walked back out in the meantime, or the
        rabbit may have been pulled into combat while the timer ran.
        """
        if not self.is_alive or not self.location:
            return

        # In combat the combat handler drives behaviour — don't bypass it
        if self.scripts.get("combat_handler"):
            return

        threats = self.ai.get_targets_in_room(THREAT_PREDICATES)
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
        threats = self.ai.get_targets_in_room(THREAT_PREDICATES)
        if threats:
            delay(
                random.uniform(2, 3),
                self._flee_reaction,
            )
            return

        # Random movement
        if random.random() < 0.2:
            self.wander()


#: What a rabbit flees from: player characters, and mobs that attack on
#: sight. A mob being a ``CombatMob`` is not enough — mice, butterflies
#: and owls are all combat-capable and none of them hunt rabbits.
THREAT_PREDICATES = (
    p_is_typeclass(FCMCharacter, AggressiveMixin),
)


# Pure-data loot-variant subclasses retired — same key/desc as Rabbit,
# only differed in loot_* defaults. Loot lives in YAML rules now
# (fcm-mobs/shard0/millholm/farms.yaml uses the base Rabbit typeclass
# with per-rule attrs + tags to express the rich / fat variants).
#
# class RabbitRich(Rabbit):
#     """Rabbit variant — carries 2 gold."""
#     loot_gold_max = AttributeProperty(2)
#
#
# class RabbitFat(Rabbit):
#     """Rabbit variant — carries 1 animal fat instead of gold."""
#     loot_gold_max = AttributeProperty(0)
#     loot_resources = AttributeProperty({45: 1})  # 1 animal fat

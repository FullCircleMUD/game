"""
A tights-wearing bandit — generic mook for Bobbin Goode's camp.

Non-LLM by design: a wandering pool of three across the camp's common
rooms keeps the place feeling lived-in without paying LLM cost for
every conversation. They greet arrivals with a scripted shout and
otherwise defer to the named lieutenants for actual conversation.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mob import CombatMob
from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.mob_abilities.weapon_mastery import WeaponMasteryMixin
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


_GREETINGS = (
    "calls out, \"Oi! Who's this then?\"",
    "raises a tankard. \"Welcome to the merriment, friend!\"",
    "squints over the firepit. \"You with the boss, or just passing?\"",
    "tugs at his ridiculous tights and gives a half-bow.",
    "grins. \"Mind the manifesto. The Friar will quiz you.\"",
    "sings, badly, half a verse of something Bobbin sings better.",
)


class TightsBandit(WeaponMasteryMixin, HumanoidWearslotsMixin, CombatMob):
    """A generic merry-band bandit. Not LLM-driven."""

    alignment_score = AttributeProperty(50)
    is_aggressive_to_players = AttributeProperty(False)

    room_description = AttributeProperty(
        "lounges in patched green-and-brown clothes and a pair of "
        "improbable striped tights, watching the camp."
    )

    base_strength = AttributeProperty(12)
    strength = AttributeProperty(12)
    base_dexterity = AttributeProperty(13)
    dexterity = AttributeProperty(13)
    base_constitution = AttributeProperty(11)
    constitution = AttributeProperty(11)
    base_intelligence = AttributeProperty(10)
    intelligence = AttributeProperty(10)
    base_wisdom = AttributeProperty(10)
    wisdom = AttributeProperty(10)
    base_charisma = AttributeProperty(10)
    charisma = AttributeProperty(10)
    base_armor_class = AttributeProperty(11)
    armor_class = AttributeProperty(11)
    base_hp_max = AttributeProperty(18)
    hp_max = AttributeProperty(18)
    hp = AttributeProperty(18)
    level = AttributeProperty(3)
    initiative_speed = AttributeProperty(2)

    damage_dice = AttributeProperty("1d6")
    damage_type = AttributeProperty(DamageType.SLASHING)
    attack_message = AttributeProperty("hacks at")
    loot_gold_max = AttributeProperty(2)

    aggro_hp_threshold = AttributeProperty(0.5)
    max_per_room = AttributeProperty(2)

    ai_tick_interval = AttributeProperty(20)

    default_weapon_masteries = {"shortsword": MasteryLevel.SKILLED.value}

    GREETING_COOLDOWN_SECONDS = 120

    def at_object_creation(self):
        super().at_object_creation()
        if not self.tags.has("merry_bandits", category="faction"):
            self.tags.add("merry_bandits", category="faction")
        weapon = MobItem.spawn_mob_item("bronze_shortsword", location=self)
        if weapon:
            self.wear(weapon)

    def at_new_arrival(self, arriving_obj):
        """Shout a greeting at arriving players, with a per-mob cooldown."""
        if not getattr(arriving_obj, "is_pc", False):
            return
        if not self.is_alive or not self.location:
            return
        if self.scripts.get("combat_handler"):
            return

        import time
        last = self.db.last_greeting_at or 0.0
        now = time.time()
        if now - last < self.GREETING_COOLDOWN_SECONDS:
            return
        self.db.last_greeting_at = now

        line = random.choice(_GREETINGS)
        self.location.msg_contents(f"|c{self.key}|n {line}")

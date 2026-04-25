"""
Butterfly — passive flying ambience for the moonpetal meadows.

Tiny, harmless, slow-wandering. Awards minimal XP, drops nothing. Exists
to make the moonpetal clearings feel alive.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.mob import CombatMob
from typeclasses.mixins.flying_mixin import FlyingMixin


class Butterfly(FlyingMixin, CombatMob):
    """A tiny butterfly drifting between the moonpetal blooms."""

    base_size = AttributeProperty(Size.TINY.value)
    size = AttributeProperty(Size.TINY.value)
    room_description = AttributeProperty(
        "drifts on slow, idle wingbeats from bloom to bloom."
    )

    # ── Flight ──
    preferred_height = AttributeProperty(1)

    # ── Stats — 1 HP glass cannon (without the cannon) ──
    hp = AttributeProperty(1)
    base_hp_max = AttributeProperty(1)
    hp_max = AttributeProperty(1)
    base_strength = AttributeProperty(1)
    strength = AttributeProperty(1)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(1)
    constitution = AttributeProperty(1)
    base_armor_class = AttributeProperty(10)
    armor_class = AttributeProperty(10)
    level = AttributeProperty(1)

    # ── Combat (only relevant if a player attacks one) ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d1")
    attack_message = AttributeProperty("flutters at")

    # ── No loot ──
    loot_gold_max = AttributeProperty(0)

    # ── XP override (atmospheric kill, not a fight) ──
    xp_award = AttributeProperty(5)

    # ── AI timing — slow drift ──
    ai_tick_interval = AttributeProperty(10)

    def ai_wander(self):
        """Slow drift between rooms. Flee combat if engaged."""
        if not self.location:
            return

        if self.scripts.get("combat_handler"):
            self.execute_cmd("flee")
            return

        if random.random() < 0.15:
            self.wander()

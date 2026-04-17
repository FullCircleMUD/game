"""
Bee Swarm — aggressive flying mob in the Hundred Acre Wood Bee Tree.

Spawns at height 1 (up in the tree). Invisible from ground level —
players only encounter them when they fly up. Aggressive, swarm
behavior. Individually weak but there are several of them.

Level 1 — a nuisance, not a serious threat to level 5 characters,
but annoying if you're not expecting them.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.flying_mixin import FlyingMixin


class BeeSwarm(FlyingMixin, AggressiveMob):
    """A swarm of angry bees. Attacks anyone who flies up to their tree."""

    size = AttributeProperty("tiny")
    room_description = AttributeProperty("buzzes angrily around the branches.")

    # ── Flight ──
    preferred_height = AttributeProperty(1)

    # ── Stats ──
    hp = AttributeProperty(8)
    base_hp_max = AttributeProperty(8)
    hp_max = AttributeProperty(8)
    base_strength = AttributeProperty(4)
    strength = AttributeProperty(4)
    base_dexterity = AttributeProperty(16)
    dexterity = AttributeProperty(16)
    base_constitution = AttributeProperty(4)
    constitution = AttributeProperty(4)
    base_armor_class = AttributeProperty(14)
    armor_class = AttributeProperty(14)
    level = AttributeProperty(1)

    # ── Combat ──
    initiative_speed = AttributeProperty(4)
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("stings")
    attack_delay_min = AttributeProperty(1)
    attack_delay_max = AttributeProperty(3)

    # ── Loot ──
    loot_gold_max = AttributeProperty(1)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.3)
    max_per_room = AttributeProperty(0)  # multiple swarms allowed

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(5)
    respawn_delay = AttributeProperty(120)

    def ai_wander(self):
        """Stay in the tree — bees don't wander."""
        # Re-ascend if knocked down
        if (
            self.location
            and not self.scripts.get("combat_handler")
            and self.room_vertical_position < self.preferred_height
        ):
            self.ascend(self.preferred_height - self.room_vertical_position)

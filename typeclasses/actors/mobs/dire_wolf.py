"""
DireWolf — aggressive predator mob that attacks players.

Extends AggressiveMob with tactical dodge behavior (25% chance per
combat tick). Retreats to the wolves den to heal when below 50% health.
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class DireWolf(AggressiveMob):
    """A massive dire wolf that attacks players on sight."""

    # ── Size ──
    size = AttributeProperty("large")

    # ── Stats — tougher than a regular wolf ──
    hp = AttributeProperty(30)
    hp_max = AttributeProperty(30)
    strength = AttributeProperty(16)
    dexterity = AttributeProperty(12)
    constitution = AttributeProperty(14)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    level = AttributeProperty(3)

    # ── Combat ──
    damage_dice = AttributeProperty("2d6")
    attack_message = AttributeProperty("savagely bites")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # ── Loot ──
    loot_resources = AttributeProperty({8: 1})  # max 1 hide
    loot_gold_max = AttributeProperty(4)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(6)
    respawn_delay = AttributeProperty(180)

    # ── Retreat ──
    den_room_tag = AttributeProperty("wolves_den")

    # ── Combat Tick ──

    def at_combat_tick(self, handler):
        """
        75% attack as normal, 25% dodge (gives enemies disadvantage).
        """
        if random.random() < 0.25:
            self.execute_cmd("dodge")

    # ── AI States ──

    def ai_retreating(self):
        """Head to den, heal."""
        if not self.location:
            return

        den_tags = self.location.tags.get(
            category="mob_area", return_list=True
        ) or []
        if self.den_room_tag in den_tags:
            if self.hp < self.hp_max:
                self.hp = min(self.hp_max, self.hp + 3)
            if self.hp >= self.hp_max:
                self.ai.set_state("wander")
            return

        self.retreat_to_spawn()

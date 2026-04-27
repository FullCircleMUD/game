"""
Mouse — tiny passive mob, harmless filler for tier-1 farms.

Behavioural opposite of Rabbit: mice ignore PCs walking in (no
at_new_arrival reaction) but try to flee combat once attacked. Used as
the entry-level mob for new players to practice combat against.

Two indistinguishable variants share the same key/desc:
- Mouse — carries no loot
- MouseGold — carries 1 gold

Spawned in Millholm farms (abandoned_farm, wheat_farm, cotton_farm).
"""

import random

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.mob import CombatMob


class Mouse(CombatMob):
    """A tiny mouse — harmless, oblivious to PCs, panics in combat."""

    base_size = AttributeProperty(Size.TINY.value)
    size = AttributeProperty(Size.TINY.value)
    room_description = AttributeProperty(
        "scurries through the dust, whiskers twitching."
    )

    # ── Stats — fragile prey ──
    hp = AttributeProperty(3)
    base_hp_max = AttributeProperty(3)
    hp_max = AttributeProperty(3)
    base_strength = AttributeProperty(2)
    strength = AttributeProperty(2)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(2)
    constitution = AttributeProperty(2)
    base_armor_class = AttributeProperty(11)
    armor_class = AttributeProperty(11)
    level = AttributeProperty(1)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d1")
    attack_message = AttributeProperty("nibbles at")

    # ── Loot — base variant carries nothing ──
    loot_gold_max = AttributeProperty(0)

    # ── XP override (lower than level*10 default — mice are tutorial fodder) ──
    xp_award = AttributeProperty(5)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(8)

    def ai_wander(self):
        """Wander quietly. Flee combat if engaged."""
        if not self.location:
            return

        if self.scripts.get("combat_handler"):
            self.execute_cmd("flee")
            return

        if random.random() < 0.2:
            self.wander()


class MouseGold(Mouse):
    """Mouse variant — carries 1 gold."""

    loot_gold_max = AttributeProperty(1)

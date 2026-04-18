"""
Heffalump — aggressive creature living in Pooh's Trap.

Stationary, aggressive on a short timer. How can you describe
something that does not exist?
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class Heffalump(AggressiveMob):
    """The Heffalump. It does not exist. Or does it?"""

    base_size = AttributeProperty(Size.LARGE.value)
    size = AttributeProperty(Size.LARGE.value)
    room_description = AttributeProperty("is here doing his thing.")

    # ── Stats (L7, 50% tougher than Woozle/Jagular) ──
    hp = AttributeProperty(75)
    base_hp_max = AttributeProperty(75)
    hp_max = AttributeProperty(75)
    base_strength = AttributeProperty(20)
    strength = AttributeProperty(20)
    base_dexterity = AttributeProperty(10)
    dexterity = AttributeProperty(10)
    base_constitution = AttributeProperty(18)
    constitution = AttributeProperty(18)
    base_armor_class = AttributeProperty(14)
    armor_class = AttributeProperty(14)
    level = AttributeProperty(6)

    # ── Combat ──
    initiative_speed = AttributeProperty(1)
    damage_dice = AttributeProperty("2d6")
    attack_message = AttributeProperty("tramples")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(4)

    # ── Behavior — aggressive on a very short timer ──
    aggro_hp_threshold = AttributeProperty(0.2)
    max_per_room = AttributeProperty(1)

    # ── Loot ──
    loot_gold_max = AttributeProperty(15)
    spawn_scrolls_max = AttributeProperty({"skilled": 1})

    # ── AI timing — short tick = fast aggro ──
    ai_tick_interval = AttributeProperty(3)
    respawn_delay = AttributeProperty(600)

    def ai_wander(self):
        """Stationary — the Heffalump stays in Pooh's Trap."""
        pass

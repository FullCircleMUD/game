"""
Heffalump — aggressive creature living in Pooh's Trap.

Stationary, aggressive on a short timer. How can you describe
something that does not exist?
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob


class Heffalump(AggressiveMob):
    """The Heffalump. It does not exist. Or does it?"""

    room_description = AttributeProperty("is here doing his thing.")

    # ── Stats (L5, tough — it might not exist but it hits hard) ──
    hp = AttributeProperty(60)
    base_hp_max = AttributeProperty(60)
    hp_max = AttributeProperty(60)
    base_strength = AttributeProperty(16)
    strength = AttributeProperty(16)
    base_dexterity = AttributeProperty(10)
    dexterity = AttributeProperty(10)
    base_constitution = AttributeProperty(16)
    constitution = AttributeProperty(16)
    base_armor_class = AttributeProperty(12)
    armor_class = AttributeProperty(12)
    level = AttributeProperty(5)

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
    loot_gold_max = AttributeProperty(10)

    # ── AI timing — short tick = fast aggro ──
    ai_tick_interval = AttributeProperty(3)
    respawn_delay = AttributeProperty(600)

    def ai_wander(self):
        """Stationary — the Heffalump stays in Pooh's Trap."""
        pass

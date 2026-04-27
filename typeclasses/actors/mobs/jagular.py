"""
Jagular — a fierce cat-like predator lurking in the Hundred Acre Wood.

Non-aggressive (passive — fights back when attacked, doesn't aggro).
Designed for level 5 solo challenge, easy for a level 5 party.
Wanders the main wood area, stays out of character houses.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from typeclasses.actors.mob import CombatMob


class Jagular(CombatMob):
    """A Jagular stalking through the Hundred Acre Wood."""

    room_description = AttributeProperty("is here stalking Pooh Bear.")

    # ── Stats (L5, tough solo, manageable for a party) ──
    hp = AttributeProperty(50)
    base_hp_max = AttributeProperty(50)
    hp_max = AttributeProperty(50)
    base_strength = AttributeProperty(15)
    strength = AttributeProperty(15)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(14)
    constitution = AttributeProperty(14)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    level = AttributeProperty(4)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("2d4")
    damage_type = AttributeProperty(DamageType.SLASHING)
    attack_message = AttributeProperty("claws at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(5)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.3)
    max_per_room = AttributeProperty(1)

    # ── Loot ──
    loot_gold_max = AttributeProperty(5)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(10)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("hundred_acre_wood_main", category="mob_area")


class JagularRecipeLoad(Jagular):
    """Jagular variant that carries a recipe instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_recipes_max = AttributeProperty({"skilled": 1})


class JagularScrollLoad(Jagular):
    """Jagular variant that carries a scroll instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_scrolls_max = AttributeProperty({"skilled": 1})

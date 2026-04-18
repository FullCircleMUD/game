"""
Woozle — a mysterious creature lurking in the Hundred Acre Wood.

Non-aggressive (passive — fights back when attacked, doesn't aggro).
Designed for level 5 solo challenge, easy for a level 5 party.
Slightly weaker than the Jagular but sneakier.
Wanders the main wood area, stays out of character houses.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.size import Size
from typeclasses.actors.mob import CombatMob


class Woozle(CombatMob):
    """A Woozle trying to look scary."""

    base_size = AttributeProperty(Size.SMALL.value)
    size = AttributeProperty(Size.SMALL.value)
    room_description = AttributeProperty("is here trying to look scary.")

    # ── Stats (L5, slightly weaker than Jagular, sneakier) ──
    hp = AttributeProperty(40)
    base_hp_max = AttributeProperty(40)
    hp_max = AttributeProperty(40)
    base_strength = AttributeProperty(13)
    strength = AttributeProperty(13)
    base_dexterity = AttributeProperty(15)
    dexterity = AttributeProperty(15)
    base_constitution = AttributeProperty(12)
    constitution = AttributeProperty(12)
    base_armor_class = AttributeProperty(14)
    armor_class = AttributeProperty(14)
    level = AttributeProperty(4)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d6+1")
    damage_type = AttributeProperty(DamageType.SLASHING)
    attack_message = AttributeProperty("swipes at")
    attack_delay_min = AttributeProperty(2)
    attack_delay_max = AttributeProperty(5)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.4)
    max_per_room = AttributeProperty(1)

    # ── Loot ──
    loot_gold_max = AttributeProperty(5)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(10)
    respawn_delay = AttributeProperty(300)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("hundred_acre_wood_main", category="mob_area")


class WoozleRecipeLoad(Woozle):
    """Woozle variant that carries a recipe instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_recipes_max = AttributeProperty({"skilled": 1})


class WoozleScrollLoad(Woozle):
    """Woozle variant that carries a scroll instead of gold."""

    loot_gold_max = AttributeProperty(0)
    spawn_scrolls_max = AttributeProperty({"skilled": 1})

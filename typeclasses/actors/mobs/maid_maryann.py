"""
Maid Maryann — the actual brains of Bobbin Goode's camp.

Stationed in the Planning Tent. Keeps the ledger, draws the marked-up
maps, drafts the manifesto's amendments. Quietly besotted with Bobbin
and absolutely will not say so.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mobs.bandit_base import BobbinBandit
from typeclasses.items.mob_items.mob_item import MobItem


class MaidMaryann(BobbinBandit):
    """The strategist. The scribe. The reason the camp still functions."""

    room_description = AttributeProperty(
        "stands at the cask-top map table with a charcoal stick in "
        "hand, weighing whatever Bobbin most recently said against "
        "what is actually possible."
    )

    llm_prompt_file = AttributeProperty("maid_maryann.md")
    llm_personality = AttributeProperty(
        "Quick, dry, and several steps ahead of everyone in the camp at "
        "any given time. Patient with Bobbin past all reason. Keeps the "
        "books because nobody else can. Goes mildly pink when caught "
        "looking at Bobbin and immediately changes the subject."
    )

    alignment_score = AttributeProperty(150)

    base_strength = AttributeProperty(10)
    strength = AttributeProperty(10)
    base_dexterity = AttributeProperty(15)
    dexterity = AttributeProperty(15)
    base_constitution = AttributeProperty(11)
    constitution = AttributeProperty(11)
    base_intelligence = AttributeProperty(17)
    intelligence = AttributeProperty(17)
    base_wisdom = AttributeProperty(15)
    wisdom = AttributeProperty(15)
    base_charisma = AttributeProperty(15)
    charisma = AttributeProperty(15)
    base_armor_class = AttributeProperty(12)
    armor_class = AttributeProperty(12)
    base_hp_max = AttributeProperty(30)
    hp_max = AttributeProperty(30)
    hp = AttributeProperty(30)
    level = AttributeProperty(5)
    initiative_speed = AttributeProperty(3)

    damage_dice = AttributeProperty("1d4")
    damage_type = AttributeProperty(DamageType.PIERCING)
    attack_message = AttributeProperty("draws a slim dagger and stabs at")
    loot_gold_max = AttributeProperty(5)

    default_weapon_masteries = {"dagger": MasteryLevel.SKILLED.value}

    def at_object_creation(self):
        super().at_object_creation()
        weapon = MobItem.spawn_mob_item("iron_dagger", location=self)
        if weapon:
            self.wear(weapon)

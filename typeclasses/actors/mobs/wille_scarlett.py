"""
Wille Scarlett — flashy duellist, vain about his outfit (the red one).

Stationed in the Yard. The first face most arrivals see after the gate.
A genuine swordsman dressed up as a stage swordsman.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mobs.bandit_base import BobbinBandit
from typeclasses.items.mob_items.mob_item import MobItem


class WilleScarlett(BobbinBandit):
    """The duellist. The peacock. Better than he looks."""

    room_description = AttributeProperty(
        "leans against the post by the lean-tos, sword on hip, a "
        "deep-red doublet very deliberately arranged."
    )

    llm_prompt_file = AttributeProperty("wille_scarlett.md")
    llm_personality = AttributeProperty(
        "Flashy, theatrical, vain about the doublet, the hair, and the "
        "footwork. Speaks with a smirk. Calls Bobbin 'boss' the way "
        "younger brothers do — affectionate, faintly mocking. Genuinely "
        "fast with a blade and quietly proud of it."
    )

    base_strength = AttributeProperty(11)
    strength = AttributeProperty(11)
    base_dexterity = AttributeProperty(17)
    dexterity = AttributeProperty(17)
    base_constitution = AttributeProperty(11)
    constitution = AttributeProperty(11)
    base_intelligence = AttributeProperty(13)
    intelligence = AttributeProperty(13)
    base_wisdom = AttributeProperty(10)
    wisdom = AttributeProperty(10)
    base_charisma = AttributeProperty(15)
    charisma = AttributeProperty(15)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    base_hp_max = AttributeProperty(35)
    hp_max = AttributeProperty(35)
    hp = AttributeProperty(35)
    level = AttributeProperty(5)
    initiative_speed = AttributeProperty(4)

    damage_dice = AttributeProperty("1d6")
    damage_type = AttributeProperty(DamageType.SLASHING)
    attack_message = AttributeProperty("flicks a blade in three quick passes at")
    loot_gold_max = AttributeProperty(6)

    default_weapon_masteries = {"shortsword": MasteryLevel.SKILLED.value}

    def at_object_creation(self):
        super().at_object_creation()
        weapon = MobItem.spawn_mob_item("bronze_shortsword", location=self)
        if weapon:
            self.wear(weapon)

"""
Lyttle Jhon — Bobbin Goode's enormous, sentimental second-in-command.

Stationed at the Training Yard. The "watch what you say" muscle of the
band; in practice he's the gentlest one in camp, runs the drills,
and cries at songs.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mobs.bandit_base import BobbinBandit
from typeclasses.items.mob_items.mob_item import MobItem


class LyttleJhon(BobbinBandit):
    """The big one. The kind one. The one with the club."""

    room_description = AttributeProperty(
        "stands beside the practice butts, a heavy club resting easily "
        "across one shoulder, watching the drill with patient eyes."
    )

    llm_prompt_file = AttributeProperty("lyttle_jhon.md")
    llm_personality = AttributeProperty(
        "Enormous, calm, and quietly sentimental. Speaks slowly, in short "
        "sentences. Loyal to Bobbin past all reason. Cries at the right "
        "kind of song and is not embarrassed about it. Patient with new "
        "arrivals. Genuinely formidable in a fight but would rather not."
    )

    base_strength = AttributeProperty(17)
    strength = AttributeProperty(17)
    base_dexterity = AttributeProperty(11)
    dexterity = AttributeProperty(11)
    base_constitution = AttributeProperty(16)
    constitution = AttributeProperty(16)
    base_intelligence = AttributeProperty(10)
    intelligence = AttributeProperty(10)
    base_wisdom = AttributeProperty(13)
    wisdom = AttributeProperty(13)
    base_charisma = AttributeProperty(11)
    charisma = AttributeProperty(11)
    base_armor_class = AttributeProperty(12)
    armor_class = AttributeProperty(12)
    base_hp_max = AttributeProperty(55)
    hp_max = AttributeProperty(55)
    hp = AttributeProperty(55)
    level = AttributeProperty(6)
    initiative_speed = AttributeProperty(1)

    damage_dice = AttributeProperty("1d8")
    damage_type = AttributeProperty(DamageType.BLUDGEONING)
    attack_message = AttributeProperty("brings a heavy club down on")
    loot_gold_max = AttributeProperty(4)

    default_weapon_masteries = {"club": MasteryLevel.SKILLED.value}

    def at_object_creation(self):
        super().at_object_creation()
        weapon = MobItem.spawn_mob_item("club", location=self)
        if weapon:
            self.wear(weapon)

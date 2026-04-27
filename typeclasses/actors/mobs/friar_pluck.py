"""
Friar Pluck — cook, unofficial chaplain, and quiet conscience of the camp.

Stationed in the Kitchen lean-to. The "Take What You Need / Pay What
You Can / Bless You Either Way" sign is his. He thinks the whole
operation is going to ruin and he stays for the stew.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mobs.bandit_base import BobbinBandit
from typeclasses.items.mob_items.mob_item import MobItem


class FriarPluck(BobbinBandit):
    """The cook. The chaplain. The disapprover-in-chief."""

    room_description = AttributeProperty(
        "stands at the lean-to with a wooden ladle in hand, sleeves "
        "pushed up, watching the cauldron with weary affection."
    )

    llm_prompt_file = AttributeProperty("friar_pluck.md")
    llm_personality = AttributeProperty(
        "Round, weather-beaten, perpetually mildly disapproving. Quietly "
        "devout. Cooks for everyone, including people he doesn't like. "
        "Speaks in dry observations. The only person in camp Bobbin will "
        "actually listen to when it matters. Pours an ale with one hand "
        "and a blessing with the other."
    )

    alignment_score = AttributeProperty(200)  # actually-good, in spite of company

    base_strength = AttributeProperty(13)
    strength = AttributeProperty(13)
    base_dexterity = AttributeProperty(10)
    dexterity = AttributeProperty(10)
    base_constitution = AttributeProperty(15)
    constitution = AttributeProperty(15)
    base_intelligence = AttributeProperty(13)
    intelligence = AttributeProperty(13)
    base_wisdom = AttributeProperty(15)
    wisdom = AttributeProperty(15)
    base_charisma = AttributeProperty(12)
    charisma = AttributeProperty(12)
    base_armor_class = AttributeProperty(11)
    armor_class = AttributeProperty(11)
    base_hp_max = AttributeProperty(38)
    hp_max = AttributeProperty(38)
    hp = AttributeProperty(38)
    level = AttributeProperty(5)
    initiative_speed = AttributeProperty(1)

    damage_dice = AttributeProperty("1d6")
    damage_type = AttributeProperty(DamageType.BLUDGEONING)
    attack_message = AttributeProperty("brings a heavy ladle down hard on")
    loot_gold_max = AttributeProperty(2)

    default_weapon_masteries = {"club": MasteryLevel.SKILLED.value}

    def at_object_creation(self):
        super().at_object_creation()
        # The "club" stands in for a stout quarterstaff / cudgel /
        # disciplinary ladle, depending on his mood.
        weapon = MobItem.spawn_mob_item("club", location=self)
        if weapon:
            self.wear(weapon)

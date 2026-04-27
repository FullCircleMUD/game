"""
Blynken — the lookout. Yes, the blind one. The arrangement works.

Stationed at the Watchtower. Operates by ear, weather, and a near-
preternatural sense of who's coming up the path. Misidentifies people
roughly half the time and is rarely wrong about anything important.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from typeclasses.actors.mobs.bandit_base import BobbinBandit


class Blynken(BobbinBandit):
    """The blind lookout. Hears more than the rest of them see."""

    room_description = AttributeProperty(
        "sits cross-legged at the watchtower platform with his head "
        "tilted slightly, listening to the path."
    )

    llm_prompt_file = AttributeProperty("blynken.md")
    llm_personality = AttributeProperty(
        "Cheerful, unflappable, and entirely blind. Greets people warmly "
        "and gets their names wrong about half the time. Has uncanny "
        "instincts about who is coming up the path and what mood they're "
        "in. Treats his blindness as a small administrative inconvenience "
        "rather than a tragedy."
    )

    base_strength = AttributeProperty(11)
    strength = AttributeProperty(11)
    base_dexterity = AttributeProperty(12)
    dexterity = AttributeProperty(12)
    base_constitution = AttributeProperty(11)
    constitution = AttributeProperty(11)
    base_intelligence = AttributeProperty(11)
    intelligence = AttributeProperty(11)
    base_wisdom = AttributeProperty(16)
    wisdom = AttributeProperty(16)
    base_charisma = AttributeProperty(13)
    charisma = AttributeProperty(13)
    base_armor_class = AttributeProperty(11)
    armor_class = AttributeProperty(11)
    base_hp_max = AttributeProperty(25)
    hp_max = AttributeProperty(25)
    hp = AttributeProperty(25)
    level = AttributeProperty(3)
    initiative_speed = AttributeProperty(2)

    # If pressed into combat, slings stones from the watchtower pouch
    damage_dice = AttributeProperty("1d4")
    damage_type = AttributeProperty(DamageType.BLUDGEONING)
    attack_message = AttributeProperty("looses a sling-stone with surprising accuracy at")
    loot_gold_max = AttributeProperty(2)

    default_weapon_masteries = {}

    def at_object_creation(self):
        super().at_object_creation()
        # No weapon to spawn — the copper horn and sling-pouch are
        # described in the room and don't need to be inventoryable
        # items at this stage.

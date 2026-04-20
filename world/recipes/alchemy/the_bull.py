from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_THE_BULL = {
    "recipe_key": "the_bull",
    "name": "Potion of the Bull",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 17: 2},  # 1 Moonpetal Essence + 2 Ogre's Cap
    "mastery_tiered": True,
}

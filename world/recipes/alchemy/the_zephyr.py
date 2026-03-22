from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_THE_ZEPHYR = {
    "recipe_key": "the_zephyr",
    "name": "Potion of the Zephyr",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 15: 2},  # 1 Moonpetal Essence + 2 Windroot
    "output_prototype": "the_zephyr",
}

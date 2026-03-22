from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_THE_BEAR = {
    "recipe_key": "the_bear",
    "name": "Potion of the Bear",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 19: 2},  # 1 Moonpetal Essence + 2 Ironbark
    "output_prototype": "the_bear",
}

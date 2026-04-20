from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_FEATHER_FALL = {
    "recipe_key": "feather_fall",
    "name": "Potion of Feather Fall",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 2, 15: 1, 14: 1},  # 2 Moonpetal Essence + 1 Windroot + 1 Bloodmoss
    "mastery_tiered": True,
}

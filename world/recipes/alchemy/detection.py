from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_DETECTION = {
    "recipe_key": "detection",
    "name": "Potion of Detection",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 2, 20: 1, 17: 1},  # 2 Moonpetal Essence + 1 Mindcap + 1 Ogre's Cap
    "mastery_tiered": True,
}

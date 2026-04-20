from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_DARKVISION = {
    "recipe_key": "darkvision",
    "name": "Potion of Darkvision",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 2, 21: 1, 20: 1},  # 2 Moonpetal Essence + 1 Sage Leaf + 1 Mindcap
    "mastery_tiered": True,
}

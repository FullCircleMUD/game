from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_WATER_BREATHING = {
    "recipe_key": "water_breathing",
    "name": "Potion of Water Breathing",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {44: 1, 13: 1, 14: 2},  # 1 Starbloom Nectar + 1 Moonpetal Essence + 2 Bloodmoss
    "mastery_tiered": True,
}

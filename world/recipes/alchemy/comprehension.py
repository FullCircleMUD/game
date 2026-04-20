from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_COMPREHENSION = {
    "recipe_key": "comprehension",
    "name": "Potion of Comprehension",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {44: 1, 13: 1, 20: 2},  # 1 Starbloom Nectar + 1 Moonpetal Essence + 2 Mindcap
    "mastery_tiered": True,
}

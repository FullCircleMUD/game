from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_HASTE = {
    "recipe_key": "haste",
    "name": "Potion of Haste",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {44: 1, 13: 1, 18: 2},  # 1 Starbloom Nectar + 1 Moonpetal Essence + 2 Vipervine
    "mastery_tiered": True,
}

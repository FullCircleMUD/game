from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BARKSKIN = {
    "recipe_key": "barkskin",
    "name": "Potion of Barkskin",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 2, 19: 1, 18: 1},  # 2 Moonpetal Essence + 1 Ironbark + 1 Vipervine
    "mastery_tiered": True,
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_HORSE_BOW = {
    "recipe_key": "horse_bow",
    "name": "Horse Bow",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 3, 9: 1},        # 3 Timber + 1 Leather (bowstring)
    "output_prototype": "horse_bow",
}

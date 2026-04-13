from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_NUNCHAKU = {
    "recipe_key": "nunchaku",
    "name": "Nunchaku",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 2, 9: 1},        # 2 Timber + 1 Leather (cord)
    "output_prototype": "nunchaku",
}

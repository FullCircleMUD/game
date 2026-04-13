from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BOLA = {
    "recipe_key": "bola",
    "name": "Bola",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 3, 9: 2},        # 3 Timber (weighted balls) + 2 Leather (cords)
    "output_prototype": "bola",
}

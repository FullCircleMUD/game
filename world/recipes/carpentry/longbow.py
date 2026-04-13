from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_LONGBOW = {
    "recipe_key": "longbow",
    "name": "Longbow",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {41: 3, 43: 1},      # 3 Ironwood Timber + 1 Wyvern Leather (bowstring)
    "output_prototype": "longbow",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_COMPOUND_BOW = {
    "recipe_key": "compound_bow",
    "name": "Compound Bow",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {41: 3, 43: 1},      # 3 Ironwood Timber + 1 Wyvern Leather (bowstring)
    "output_prototype": "compound_bow",
}

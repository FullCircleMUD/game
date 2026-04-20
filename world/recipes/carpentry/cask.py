from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_CASK = {
    "recipe_key": "cask",
    "name": "Cask",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 4},              # 4 Timber (resource_id 7)
    "output_prototype": "cask",
}

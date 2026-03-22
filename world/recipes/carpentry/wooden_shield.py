from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_WOODEN_SHIELD = {
    "recipe_key": "wooden_shield",
    "name": "Wooden Shield",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 3},              # 3 Timber (resource_id 7)
    "output_prototype": "wooden_shield",
}

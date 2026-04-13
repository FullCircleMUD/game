from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_WOODEN_GREATCLUB = {
    "recipe_key": "wooden_greatclub",
    "name": "Wooden Greatclub",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 4},              # 4 Timber (resource_id 7)
    "output_prototype": "wooden_greatclub",
}

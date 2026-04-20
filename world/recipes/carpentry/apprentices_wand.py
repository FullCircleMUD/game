from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_APPRENTICES_WAND = {
    "recipe_key": "apprentices_wand",
    "name": "Apprentice's Wand",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 1},              # 1 Timber (resource_id 7)
    "output_prototype": "apprentices_wand",
}

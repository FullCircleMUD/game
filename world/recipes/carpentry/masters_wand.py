from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_MASTERS_WAND = {
    "recipe_key": "masters_wand",
    "name": "Master's Wand",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {41: 1},             # 1 Ironwood Timber (resource_id 41)
    "output_prototype": "masters_wand",
}

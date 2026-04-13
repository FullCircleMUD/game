from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRONWOOD_HAFT = {
    "recipe_key": "ironwood_haft",
    "name": "Ironwood Haft",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {41: 2},              # 2 Ironwood Timber (resource_id 41)
    "output_prototype": "ironwood_haft",
}

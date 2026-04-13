from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_SAI = {
    "recipe_key": "iron_sai",
    "name": "Iron Sai",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 2},              # 2 Iron Ingot (resource_id 5)
    "output_prototype": "iron_sai",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_SAI = {
    "recipe_key": "bronze_sai",
    "name": "Bronze Sai",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 2},              # 2 Bronze Ingot (resource_id 32)
    "output_prototype": "bronze_sai",
}

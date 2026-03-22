from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_SHORTSWORD = {
    "recipe_key": "bronze_shortsword",
    "name": "Bronze Shortsword",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 2},             # 2 Bronze Ingot (resource_id 32)
    "output_prototype": "bronze_shortsword",
}

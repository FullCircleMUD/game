from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_GREATSWORD = {
    "recipe_key": "bronze_greatsword",
    "name": "Bronze Greatsword",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 4},              # 4 Bronze Ingot (resource_id 32)
    "output_prototype": "bronze_greatsword",
}

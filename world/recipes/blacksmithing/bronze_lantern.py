from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_LANTERN = {
    "recipe_key": "bronze_lantern",
    "name": "Bronze Lantern",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 1},             # 1 Bronze Ingot (resource_id 32)
    "output_prototype": "bronze_lantern",
}

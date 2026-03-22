from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_LONGSWORD = {
    "recipe_key": "iron_longsword",
    "name": "Iron Longsword",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 3},              # 3 Iron Ingot (resource_id 5)
    "output_prototype": "iron_longsword",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_LANCE = {
    "recipe_key": "iron_lance",
    "name": "Iron Lance",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 1},              # 1 Iron Ingot (resource_id 5)
    "nft_ingredients": {"shaft": 1},    # 1 Shaft (carpenter component)
    "output_prototype": "iron_lance",
}

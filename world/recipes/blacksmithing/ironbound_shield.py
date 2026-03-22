from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRONBOUND_SHIELD = {
    "recipe_key": "ironbound_shield",
    "name": "Ironbound Shield",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 1},              # 1 Iron Ingot (resource_id 5)
    "nft_ingredients": {"wooden_shield": 1},  # 1 Wooden Shield (carpenter item)
    "output_prototype": "ironbound_shield",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_SPIKED_GREATCLUB = {
    "recipe_key": "iron_spiked_greatclub",
    "name": "Iron Spiked Greatclub",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 1},                          # 1 Iron Ingot (resource_id 5)
    "nft_ingredients": {"wooden_greatclub": 1},     # 1 Wooden Greatclub (carpenter item)
    "output_prototype": "iron_spiked_greatclub",
}

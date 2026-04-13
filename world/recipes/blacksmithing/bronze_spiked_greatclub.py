from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_SPIKED_GREATCLUB = {
    "recipe_key": "bronze_spiked_greatclub",
    "name": "Bronze Spiked Greatclub",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 1},                         # 1 Bronze Ingot (resource_id 32)
    "nft_ingredients": {"wooden_greatclub": 1},     # 1 Wooden Greatclub (carpenter item)
    "output_prototype": "bronze_spiked_greatclub",
}

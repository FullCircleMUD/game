from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_SPEAR = {
    "recipe_key": "bronze_spear",
    "name": "Bronze Spear",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 1},             # 1 Bronze Ingot (resource_id 32)
    "nft_ingredients": {"shaft": 1},    # 1 Shaft (carpenter component)
    "output_prototype": "bronze_spear",
}

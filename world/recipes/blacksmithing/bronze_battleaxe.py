from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_BATTLEAXE = {
    "recipe_key": "bronze_battleaxe",
    "name": "Bronze Battleaxe",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 3},              # 3 Bronze Ingot (resource_id 32)
    "nft_ingredients": {"haft": 1},      # 1 Haft (carpenter component)
    "output_prototype": "bronze_battleaxe",
}

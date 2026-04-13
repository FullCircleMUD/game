from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_BATTLEAXE = {
    "recipe_key": "iron_battleaxe",
    "name": "Iron Battleaxe",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 3},              # 3 Iron Ingot (resource_id 5)
    "nft_ingredients": {"haft": 1},     # 1 Haft (carpenter component)
    "output_prototype": "iron_battleaxe",
}

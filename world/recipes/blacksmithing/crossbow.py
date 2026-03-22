from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_CROSSBOW = {
    "recipe_key": "crossbow",
    "name": "Crossbow",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 2},              # 2 Iron Ingot (resource_id 5)
    "nft_ingredients": {"stock": 1},    # 1 Stock (carpenter component)
    "output_prototype": "crossbow",
}

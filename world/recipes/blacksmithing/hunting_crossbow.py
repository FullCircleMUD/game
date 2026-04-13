from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_HUNTING_CROSSBOW = {
    "recipe_key": "hunting_crossbow",
    "name": "Hunting Crossbow",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 2},              # 2 Iron Ingot (resource_id 5)
    "nft_ingredients": {"stock": 1},    # 1 Stock (carpenter component)
    "output_prototype": "hunting_crossbow",
}

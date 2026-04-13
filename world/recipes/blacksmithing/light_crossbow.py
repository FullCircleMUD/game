from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_LIGHT_CROSSBOW = {
    "recipe_key": "light_crossbow",
    "name": "Light Crossbow",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 2},             # 2 Bronze Ingot (resource_id 32)
    "nft_ingredients": {"stock": 1},    # 1 Stock (carpenter component)
    "output_prototype": "light_crossbow",
}

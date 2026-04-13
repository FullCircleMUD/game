from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_HEAVY_CROSSBOW = {
    "recipe_key": "heavy_crossbow",
    "name": "Heavy Crossbow",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 2},                        # 2 Steel Ingot (resource_id 37)
    "nft_ingredients": {"ironwood_stock": 1},      # 1 Ironwood Stock
    "output_prototype": "heavy_crossbow",
}

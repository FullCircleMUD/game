from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ARBALEST = {
    "recipe_key": "arbalest",
    "name": "Arbalest",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 2},                        # 2 Adamantine Ingot (resource_id 38)
    "nft_ingredients": {"ironwood_stock": 1},      # 1 Ironwood Stock
    "output_prototype": "arbalest",
}

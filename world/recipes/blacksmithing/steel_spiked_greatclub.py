from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STEEL_SPIKED_GREATCLUB = {
    "recipe_key": "steel_spiked_greatclub",
    "name": "Steel Spiked Greatclub",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 1},                          # 1 Steel Ingot (resource_id 37)
    "nft_ingredients": {"ironwood_greatclub": 1},    # 1 Ironwood Greatclub (carpenter item)
    "output_prototype": "steel_spiked_greatclub",
}

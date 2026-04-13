from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STEEL_SPEAR = {
    "recipe_key": "steel_spear",
    "name": "Steel Spear",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 1},                        # 1 Steel Ingot (resource_id 37)
    "nft_ingredients": {"ironwood_shaft": 1},      # 1 Ironwood Shaft
    "output_prototype": "steel_spear",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STEEL_TIPPED_STAFF = {
    "recipe_key": "steel_tipped_staff",
    "name": "Steel-Tipped Staff",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 1},                        # 1 Steel Ingot (resource_id 37)
    "nft_ingredients": {"ironwood_staff": 1},      # 1 Ironwood Staff (carpenter item)
    "output_prototype": "steel_tipped_staff",
}

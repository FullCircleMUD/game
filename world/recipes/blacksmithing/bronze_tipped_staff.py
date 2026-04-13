from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRONZE_TIPPED_STAFF = {
    "recipe_key": "bronze_tipped_staff",
    "name": "Bronze-Tipped Staff",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {32: 1},                      # 1 Bronze Ingot (resource_id 32)
    "nft_ingredients": {"quarterstaff": 1},      # 1 Quarterstaff (carpenter item)
    "output_prototype": "bronze_tipped_staff",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_TIPPED_STAFF = {
    "recipe_key": "iron_tipped_staff",
    "name": "Iron-Tipped Staff",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 1},                       # 1 Iron Ingot (resource_id 5)
    "nft_ingredients": {"quarterstaff": 1},      # 1 Quarterstaff (carpenter item)
    "output_prototype": "iron_tipped_staff",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_TIPPED_STAFF = {
    "recipe_key": "adamantine_tipped_staff",
    "name": "Adamantine-Tipped Staff",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 1},                        # 1 Adamantine Ingot (resource_id 38)
    "nft_ingredients": {"ironwood_staff": 1},      # 1 Ironwood Staff (carpenter item)
    "output_prototype": "adamantine_tipped_staff",
}

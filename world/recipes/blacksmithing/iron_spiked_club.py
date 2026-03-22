from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_SPIKED_CLUB = {
    "recipe_key": "iron_spiked_club",
    "name": "Iron Spiked Club",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 1},              # 1 Iron Ingot (resource_id 5)
    "nft_ingredients": {"club": 1},     # 1 Club (carpenter item)
    "output_prototype": "iron_spiked_club",
}

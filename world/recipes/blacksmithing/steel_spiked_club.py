from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STEEL_SPIKED_CLUB = {
    "recipe_key": "steel_spiked_club",
    "name": "Steel Spiked Club",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 1},                       # 1 Steel Ingot (resource_id 37)
    "nft_ingredients": {"ironwood_club": 1},      # 1 Ironwood Club (carpenter item)
    "output_prototype": "steel_spiked_club",
}

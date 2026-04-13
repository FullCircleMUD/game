from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_SPIKED_CLUB = {
    "recipe_key": "adamantine_spiked_club",
    "name": "Adamantine Spiked Club",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 1},                       # 1 Adamantine Ingot (resource_id 38)
    "nft_ingredients": {"ironwood_club": 1},      # 1 Ironwood Club (carpenter item)
    "output_prototype": "adamantine_spiked_club",
}

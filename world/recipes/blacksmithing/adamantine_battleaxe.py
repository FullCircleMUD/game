from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_BATTLEAXE = {
    "recipe_key": "adamantine_battleaxe",
    "name": "Adamantine Battleaxe",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 3},                       # 3 Adamantine Ingot (resource_id 38)
    "nft_ingredients": {"ironwood_haft": 1},      # 1 Ironwood Haft
    "output_prototype": "adamantine_battleaxe",
}

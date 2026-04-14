from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ARCHMAGES_WAND = {
    "recipe_key": "archmages_wand",
    "name": "Archmage's Wand",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {41: 1},             # 1 Ironwood Timber (resource_id 41)
    "output_prototype": "archmages_wand",
}

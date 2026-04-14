from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_WIZARDS_WAND = {
    "recipe_key": "wizards_wand",
    "name": "Wizard's Wand",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {41: 1},             # 1 Ironwood Timber (resource_id 41)
    "output_prototype": "wizards_wand",
}

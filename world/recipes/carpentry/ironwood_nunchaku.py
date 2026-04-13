from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRONWOOD_NUNCHAKU = {
    "recipe_key": "ironwood_nunchaku",
    "name": "Ironwood Nunchaku",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {41: 2, 43: 1},      # 2 Ironwood Timber + 1 Wyvern Leather
    "output_prototype": "ironwood_nunchaku",
}

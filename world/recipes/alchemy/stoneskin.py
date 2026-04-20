from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STONESKIN = {
    "recipe_key": "stoneskin",
    "name": "Potion of Stoneskin",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {44: 1, 13: 1, 17: 1, 19: 1},  # 1 Starbloom Nectar + 1 Moonpetal Essence + 1 Ogre's Cap + 1 Ironbark
    "mastery_tiered": True,
}

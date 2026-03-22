from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_LIFES_ESSENCE = {
    "recipe_key": "lifes_essence",
    "name": "Potion of Life's Essence",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 14: 2},  # 1 Moonpetal Essence + 2 Bloodmoss
    "output_prototype": "lifes_essence",
}

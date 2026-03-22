from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_CATS_GRACE = {
    "recipe_key": "cats_grace",
    "name": "Potion of Cat's Grace",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 18: 2},  # 1 Moonpetal Essence + 2 Vipervine
    "output_prototype": "cats_grace",
}

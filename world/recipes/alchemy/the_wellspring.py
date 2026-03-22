from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_THE_WELLSPRING = {
    "recipe_key": "the_wellspring",
    "name": "Potion of the Wellspring",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 16: 2},  # 1 Moonpetal Essence + 2 Arcane Dust
    "output_prototype": "the_wellspring",
}

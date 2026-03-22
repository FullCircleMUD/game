from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_FOXS_CUNNING = {
    "recipe_key": "foxs_cunning",
    "name": "Potion of Fox's Cunning",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 20: 2},  # 1 Moonpetal Essence + 2 Mindcap
    "output_prototype": "foxs_cunning",
}

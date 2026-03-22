from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_OWLS_INSIGHT = {
    "recipe_key": "owls_insight",
    "name": "Potion of Owl's Insight",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 21: 2},  # 1 Moonpetal Essence + 2 Sage Leaf
    "output_prototype": "owls_insight",
}

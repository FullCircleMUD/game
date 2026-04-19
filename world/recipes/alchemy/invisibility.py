from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_INVISIBILITY = {
    "recipe_key": "invisibility",
    "name": "Potion of Invisibility",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 2, 16: 1, 22: 1},  # 2 Moonpetal Essence + 1 Arcane Dust + 1 Siren Petal
    "mastery_tiered": True,
}

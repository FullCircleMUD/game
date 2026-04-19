from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_SILVER_TONGUE = {
    "recipe_key": "silver_tongue",
    "name": "Potion of the Silver Tongue",
    "skill": skills.ALCHEMIST,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.APOTHECARY,
    "ingredients": {13: 1, 22: 2},  # 1 Moonpetal Essence + 2 Siren Petal
    "mastery_tiered": True,
}

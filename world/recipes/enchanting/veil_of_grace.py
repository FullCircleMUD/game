from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_VEIL_OF_GRACE = {
    "recipe_key": "veil_of_grace",
    "name": "Veil of Grace",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {15: 2},              # 2 Arcane Dust (resource_id 15)
    "nft_ingredients": {"veil": 1},
    "output_prototype": "veil_of_grace",
}

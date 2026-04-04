from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ROGUES_BANDANA = {
    "recipe_key": "rogues_bandana",
    "name": "Rogue's Bandana",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {16: 2},              # 2 Arcane Dust (resource_id 16)
    "nft_ingredients": {"bandana": 1},
    "output_prototype": "rogues_bandana",
}

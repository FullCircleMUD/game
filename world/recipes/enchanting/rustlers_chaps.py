from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_RUSTLERS_CHAPS = {
    "recipe_key": "rustlers_chaps",
    "name": "Rustler's Chaps",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {15: 2},              # 2 Arcane Dust (resource_id 15)
    "nft_ingredients": {"leather_pants": 1},
    "output_prototype": "rustlers_chaps",
}

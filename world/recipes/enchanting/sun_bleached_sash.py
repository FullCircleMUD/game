from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_SUN_BLEACHED_SASH = {
    "recipe_key": "sun_bleached_sash",
    "name": "Sun Bleached Sash",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {16: 2},              # 2 Arcane Dust (resource_id 16)
    "nft_ingredients": {"sash": 1},
    "output_prototype": "sun_bleached_sash",
}

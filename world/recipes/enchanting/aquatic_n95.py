from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_AQUATIC_N95 = {
    "recipe_key": "aquatic_n95",
    "name": "Aquatic N95",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {17: 2},              # 2 Windroot (resource_id 17)
    "nft_ingredients": {"n95_mask": 1},
    "output_prototype": "aquatic_n95",
}

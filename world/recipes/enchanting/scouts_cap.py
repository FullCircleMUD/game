from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_SCOUTS_CAP = {
    "recipe_key": "scouts_cap",
    "name": "Scout's Cap",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {15: 2},              # 2 Arcane Dust (resource_id 15)
    "nft_ingredients": {"leather_cap": 1},
    "output_prototype": "scouts_cap",
}

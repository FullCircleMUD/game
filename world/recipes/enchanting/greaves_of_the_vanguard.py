from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_GREAVES_OF_THE_VANGUARD = {
    "recipe_key": "greaves_of_the_vanguard",
    "name": "Greaves of the Vanguard",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {15: 2},              # 2 Arcane Dust (resource_id 15)
    "nft_ingredients": {"bronze_greaves": 1},
    "output_prototype": "greaves_of_the_vanguard",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRACERS_OF_DEFLECTION = {
    "recipe_key": "bracers_of_deflection",
    "name": "Bracers of Deflection",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {15: 2},              # 2 Arcane Dust (resource_id 15)
    "nft_ingredients": {"bronze_bracers": 1},
    "output_prototype": "bracers_of_deflection",
}

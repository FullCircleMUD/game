from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_PUGILISTS_GLOVES = {
    "recipe_key": "pugilists_gloves",
    "name": "Pugilist's Gloves",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {16: 2},              # 2 Arcane Dust (resource_id 16)
    "nft_ingredients": {"leather_gloves": 1},
    "output_prototype": "pugilists_gloves",
}

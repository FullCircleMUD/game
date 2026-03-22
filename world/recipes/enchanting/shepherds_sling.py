from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_SHEPHERDS_SLING = {
    "recipe_key": "shepherds_sling",
    "name": "Shepherd's Sling",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {15: 2},              # 2 Arcane Dust (resource_id 15)
    "nft_ingredients": {"sling": 1},     # 1 Sling (leatherworker item)
    "output_prototype": "shepherds_sling",
}

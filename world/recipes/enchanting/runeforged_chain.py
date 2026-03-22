from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_RUNEFORGED_CHAIN = {
    "recipe_key": "runeforged_chain",
    "name": "Runeforged Chain",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {15: 2},              # 2 Arcane Dust (resource_id 15)
    "nft_ingredients": {"copper_chain": 1},
    "output_prototype": "runeforged_chain",
}

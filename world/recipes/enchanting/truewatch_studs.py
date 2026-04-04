from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_TRUEWATCH_STUDS = {
    "recipe_key": "truewatch_studs",
    "name": "Truewatch Studs",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {16: 2},              # 2 Arcane Dust (resource_id 16)
    "nft_ingredients": {"copper_studs": 1},
    "output_prototype": "truewatch_studs",
}

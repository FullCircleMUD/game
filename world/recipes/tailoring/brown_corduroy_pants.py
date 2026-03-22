from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BROWN_CORDUROY_PANTS = {
    "recipe_key": "brown_corduroy_pants",
    "name": "Brown Corduroy Pants",
    "skill": skills.TAILOR,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.TAILOR,
    "ingredients": {11: 3},              # 3 Cloth (resource_id 11)
    "output_prototype": "brown_corduroy_pants",
}

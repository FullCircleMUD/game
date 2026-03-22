from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_COPPER_BANGLE = {
    "recipe_key": "copper_bangle",
    "name": "Copper Bangle",
    "skill": skills.JEWELLER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.JEWELLER,
    "ingredients": {24: 1},              # 1 Copper Ingot
    "output_prototype": "copper_bangle",
}

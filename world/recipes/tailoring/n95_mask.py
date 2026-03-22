from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_N95_MASK = {
    "recipe_key": "n95_mask",
    "name": "N95 Mask",
    "skill": skills.TAILOR,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.TAILOR,
    "ingredients": {11: 1},              # 1 Cloth (resource_id 11)
    "output_prototype": "n95_mask",
}

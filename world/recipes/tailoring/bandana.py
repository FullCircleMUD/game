from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BANDANA = {
    "recipe_key": "bandana",
    "name": "Bandana",
    "skill": skills.TAILOR,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.TAILOR,
    "ingredients": {11: 1},              # 1 Cloth (resource_id 11)
    "output_prototype": "bandana",
}

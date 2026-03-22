from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_SCARF = {
    "recipe_key": "scarf",
    "name": "Scarf",
    "skill": skills.TAILOR,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.TAILOR,
    "ingredients": {11: 2},              # 2 Cloth (resource_id 11)
    "output_prototype": "scarf",
}

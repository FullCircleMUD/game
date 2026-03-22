from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_CLOAK = {
    "recipe_key": "cloak",
    "name": "Cloak",
    "skill": skills.TAILOR,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.TAILOR,
    "ingredients": {11: 3},              # 3 Cloth (resource_id 11)
    "output_prototype": "cloak",
}

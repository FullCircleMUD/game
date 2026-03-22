from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_WARRIORS_WRAPS = {
    "recipe_key": "warriors_wraps",
    "name": "Warrior's Wraps",
    "skill": skills.TAILOR,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.TAILOR,
    "ingredients": {11: 2},              # 2 Cloth (resource_id 11)
    "output_prototype": "warriors_wraps",
}

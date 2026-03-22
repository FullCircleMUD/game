from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_GAMBESON = {
    "recipe_key": "gambeson",
    "name": "Gambeson",
    "skill": skills.TAILOR,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.TAILOR,
    "ingredients": {11: 4},              # 4 Cloth (resource_id 11)
    "output_prototype": "gambeson",
}

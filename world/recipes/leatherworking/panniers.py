from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_PANNIERS = {
    "recipe_key": "panniers",
    "name": "Panniers",
    "skill": skills.LEATHERWORKER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.LEATHERSHOP,
    "ingredients": {9: 4},              # 4 Leather (resource_id 9)
    "output_prototype": "panniers",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BACKPACK = {
    "recipe_key": "backpack",
    "name": "Backpack",
    "skill": skills.LEATHERWORKER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.LEATHERSHOP,
    "ingredients": {9: 4},              # 4 Leather (resource_id 9)
    "output_prototype": "backpack",
}

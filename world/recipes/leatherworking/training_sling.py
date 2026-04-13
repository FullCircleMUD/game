from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_TRAINING_SLING = {
    "recipe_key": "training_sling",
    "name": "Training Sling",
    "skill": skills.LEATHERWORKER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.LEATHERSHOP,
    "ingredients": {9: 1},              # 1 Leather (resource_id 9)
    "output_prototype": "training_sling",
}

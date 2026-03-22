from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_TRAINING_LANCE = {
    "recipe_key": "training_lance",
    "name": "Training Lance",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 6},              # 6 Timber (resource_id 7)
    "output_prototype": "training_lance",
}

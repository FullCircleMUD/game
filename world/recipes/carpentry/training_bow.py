from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_TRAINING_BOW = {
    "recipe_key": "training_bow",
    "name": "Training Bow",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 3, 9: 1},        # 3 Timber + 1 Leather (bowstring)
    "output_prototype": "training_bow",
}

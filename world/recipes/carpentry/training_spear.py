from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_TRAINING_SPEAR = {
    "recipe_key": "training_spear",
    "name": "Training Spear",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 1},              # 1 Timber (resource_id 7)
    "nft_ingredients": {"shaft": 1},    # 1 Shaft (carpenter component)
    "output_prototype": "training_spear",
}

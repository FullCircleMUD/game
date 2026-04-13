from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_TRAINING_CROSSBOW = {
    "recipe_key": "training_crossbow",
    "name": "Training Crossbow",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 2, 9: 1},        # 2 Timber + 1 Leather (bowstring)
    "nft_ingredients": {"stock": 1},    # 1 Stock (carpenter component)
    "output_prototype": "training_crossbow",
}

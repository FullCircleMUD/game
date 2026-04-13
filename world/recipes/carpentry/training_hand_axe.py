from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_TRAINING_HAND_AXE = {
    "recipe_key": "training_hand_axe",
    "name": "Training Hand Axe",
    "skill": skills.CARPENTER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WOODSHOP,
    "ingredients": {7: 2},              # 2 Timber (resource_id 7)
    "nft_ingredients": {"haft": 1},     # 1 Haft (carpenter component)
    "output_prototype": "training_hand_axe",
}

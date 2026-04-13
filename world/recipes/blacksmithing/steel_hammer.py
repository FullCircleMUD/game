from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STEEL_HAMMER = {
    "recipe_key": "steel_hammer",
    "name": "Steel Hammer",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 2},                       # 2 Steel Ingot (resource_id 37)
    "nft_ingredients": {"ironwood_haft": 1},      # 1 Ironwood Haft
    "output_prototype": "steel_hammer",
}

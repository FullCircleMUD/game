from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_LEATHER_ARMOR = {
    "recipe_key": "leather_armor",
    "name": "Leather Armor",
    "skill": skills.LEATHERWORKER,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.LEATHERSHOP,
    "ingredients": {9: 4},              # 4 Leather (resource_id 9)
    "nft_ingredients": {"gambeson": 1, "leather_straps": 1},
    "output_prototype": "leather_armor",
}

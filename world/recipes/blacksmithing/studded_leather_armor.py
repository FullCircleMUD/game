from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STUDDED_LEATHER_ARMOR = {
    "recipe_key": "studded_leather_armor",
    "name": "Studded Leather Armor",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 2},              # 2 Iron Ingot (resource_id 5)
    "nft_ingredients": {"leather_armor": 1},  # 1 Leather Armor (leatherworker item)
    "output_prototype": "studded_leather_armor",
}

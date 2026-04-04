from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_WARDENS_LEATHER = {
    "recipe_key": "wardens_leather",
    "name": "Warden's Leather",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {16: 2},              # 2 Arcane Dust (resource_id 16)
    "nft_ingredients": {"leather_armor": 1},  # 1 Leather Armor (leatherworker item)
    "output_prototype": "wardens_leather",
}

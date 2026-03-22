from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_SKYDANCERS_RING = {
    "recipe_key": "skydancers_ring",
    "name": "Skydancer's Ring",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {17: 2},              # 2 Windroot (resource_id 17)
    "nft_ingredients": {"pewter_ring": 1},
    "output_prototype": "skydancers_ring",
}

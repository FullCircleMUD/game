from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_HAND_AXE = {
    "recipe_key": "adamantine_hand_axe",
    "name": "Adamantine Hand Axe",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 2},                       # 2 Adamantine Ingot (resource_id 38)
    "nft_ingredients": {"ironwood_haft": 1},      # 1 Ironwood Haft
    "output_prototype": "adamantine_hand_axe",
}

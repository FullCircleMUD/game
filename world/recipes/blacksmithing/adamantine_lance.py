from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_LANCE = {
    "recipe_key": "adamantine_lance",
    "name": "Adamantine Lance",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 1},                        # 1 Adamantine Ingot (resource_id 38)
    "nft_ingredients": {"ironwood_shaft": 1},      # 1 Ironwood Shaft
    "output_prototype": "adamantine_lance",
}

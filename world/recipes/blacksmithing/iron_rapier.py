from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_RAPIER = {
    "recipe_key": "iron_rapier",
    "name": "Iron Rapier",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 3},              # 3 Iron Ingot (resource_id 5)
    "output_prototype": "iron_rapier",
}

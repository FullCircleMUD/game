from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_IRON_GREATSWORD = {
    "recipe_key": "iron_greatsword",
    "name": "Iron Greatsword",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {5: 4},              # 4 Iron Ingot (resource_id 5)
    "output_prototype": "iron_greatsword",
}

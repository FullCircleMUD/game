from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STEEL_GREATSWORD = {
    "recipe_key": "steel_greatsword",
    "name": "Steel Greatsword",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 4},              # 4 Steel Ingot (resource_id 37)
    "output_prototype": "steel_greatsword",
}

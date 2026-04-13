from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_STEEL_RAPIER = {
    "recipe_key": "steel_rapier",
    "name": "Steel Rapier",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {37: 3},              # 3 Steel Ingot (resource_id 37)
    "output_prototype": "steel_rapier",
}

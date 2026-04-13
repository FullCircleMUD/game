from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_DAGGER = {
    "recipe_key": "adamantine_dagger",
    "name": "Adamantine Dagger",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 1},              # 1 Adamantine Ingot (resource_id 38)
    "output_prototype": "adamantine_dagger",
}

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_LONGSWORD = {
    "recipe_key": "adamantine_longsword",
    "name": "Adamantine Longsword",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 3},              # 3 Adamantine Ingot (resource_id 38)
    "output_prototype": "adamantine_longsword",
}

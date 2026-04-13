from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_SHURIKEN = {
    "recipe_key": "adamantine_shuriken",
    "name": "Adamantine Shuriken",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 1},              # 1 Adamantine Ingot (resource_id 38)
    "output_prototype": "adamantine_shuriken",
}

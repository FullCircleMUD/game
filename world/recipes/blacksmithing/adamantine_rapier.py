from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ADAMANTINE_RAPIER = {
    "recipe_key": "adamantine_rapier",
    "name": "Adamantine Rapier",
    "skill": skills.BLACKSMITH,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.SMITHY,
    "ingredients": {38: 3},              # 3 Adamantine Ingot (resource_id 38)
    "output_prototype": "adamantine_rapier",
}

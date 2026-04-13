from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_WYVERN_LEATHER_SLING = {
    "recipe_key": "wyvern_leather_sling",
    "name": "Wyvern Leather Sling",
    "skill": skills.LEATHERWORKER,
    "min_mastery": MasteryLevel.MASTER,
    "crafting_type": RoomCraftingType.LEATHERSHOP,
    "ingredients": {43: 1},              # 1 Wyvern Leather (resource_id 43)
    "output_prototype": "wyvern_leather_sling",
}

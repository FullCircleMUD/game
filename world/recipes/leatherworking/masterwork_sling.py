from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_MASTERWORK_SLING = {
    "recipe_key": "masterwork_sling",
    "name": "Masterwork Sling",
    "skill": skills.LEATHERWORKER,
    "min_mastery": MasteryLevel.GRANDMASTER,
    "crafting_type": RoomCraftingType.LEATHERSHOP,
    "ingredients": {43: 2},              # 2 Wyvern Leather (resource_id 43)
    "output_prototype": "masterwork_sling",
}

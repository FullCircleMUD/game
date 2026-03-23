from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_COG = {
    "recipe_key": "cog",
    "name": "Cog",
    "skill": skills.SHIPWRIGHT,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.SHIPYARD,
    "ingredients": {
        7: 50,    # 50 Timber
        11: 10,   # 10 Cloth
    },
    "output_prototype": "cog",
}

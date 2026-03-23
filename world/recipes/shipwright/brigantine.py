from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_BRIGANTINE = {
    "recipe_key": "brigantine",
    "name": "Brigantine",
    "skill": skills.SHIPWRIGHT,
    "min_mastery": MasteryLevel.EXPERT,
    "crafting_type": RoomCraftingType.SHIPYARD,
    "ingredients": {
        7: 200,   # 200 Timber
        11: 50,   # 50 Cloth
        24: 40,   # 40 Copper Ingot
        5: 20,    # 20 Iron Ingot
    },
    "output_prototype": "brigantine",
}

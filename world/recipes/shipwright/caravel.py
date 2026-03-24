from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_CARAVEL = {
    "recipe_key": "caravel",
    "name": "Caravel",
    "skill": skills.SHIPWRIGHT,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.SHIPYARD,
    "ingredients": {
        7: 100,   # 100 Timber
        11: 25,   # 25 Cloth
        24: 20,   # 20 Copper Ingot
    },
    "output_prototype": "caravel",
    "bank_funded": True,
}

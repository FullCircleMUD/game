from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_PEWTER_CHAIN = {
    "recipe_key": "pewter_chain",
    "name": "Pewter Chain",
    "skill": skills.JEWELLER,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.JEWELLER,
    "ingredients": {29: 1},              # 1 Pewter Ingot
    "output_prototype": "pewter_chain",
}

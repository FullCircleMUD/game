from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_PEWTER_BRACELET = {
    "recipe_key": "pewter_bracelet",
    "name": "Pewter Bracelet",
    "skill": skills.JEWELLER,
    "min_mastery": MasteryLevel.SKILLED,
    "crafting_type": RoomCraftingType.JEWELLER,
    "ingredients": {29: 1},              # 1 Pewter Ingot
    "output_prototype": "pewter_bracelet",
}

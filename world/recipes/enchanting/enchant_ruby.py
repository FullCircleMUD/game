from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills

RECIPE_ENCHANT_RUBY = {
    "recipe_key": "enchant_ruby",
    "name": "Enchanted Ruby",
    "skill": skills.ENCHANTING,
    "min_mastery": MasteryLevel.BASIC,
    "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
    "ingredients": {16: 2, 33: 1},       # 2 Arcane Dust + 1 Ruby
    "output_table": "enchanted_ruby",     # signals roll table in gem_tables.py
    "output_prototype": "enchanted_ruby",
}

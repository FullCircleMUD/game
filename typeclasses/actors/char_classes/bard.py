from enums.abilities_enum import Ability
from typeclasses.actors.char_classes.char_class_base import CharClassBase


PROGRESSION = {
    # Early Levels (1-10) - Learning the basics
    1: {"weapon_skill_pts": 2, "class_skill_pts": 3, "general_skill_pts": 3, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    2: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    3: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    4: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    5: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:4   class:11  general:7   hp:30   mana:30  move:20

    6: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    7: {"weapon_skill_pts": 0, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    8: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    9: {"weapon_skill_pts": 0, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    10: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:7   class:19  general:14  hp:60   mana:60  move:40

    11: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    12: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    13: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    14: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    15: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:9   class:28  general:21  hp:90   mana:90  move:60

    16: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    17: {"weapon_skill_pts": 0, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    18: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    19: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    20: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:12  class:37  general:28  hp:120  mana:120 move:80

    21: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    22: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    23: {"weapon_skill_pts": 0, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    24: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    25: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:14  class:46  general:36  hp:150  mana:150 move:100

    # High Levels (26-40) - Master bard
    26: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    27: {"weapon_skill_pts": 0, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    28: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    29: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    30: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:17  class:55  general:43  hp:180  mana:180 move:120

    31: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    32: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    33: {"weapon_skill_pts": 0, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    34: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    35: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:19  class:64  general:51  hp:210  mana:210 move:140

    36: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    37: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    38: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    39: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    40: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:23  class:73  general:59  hp:240  mana:240 move:160
}


BARD = CharClassBase(
    key="bard",
    display_name="Bard",
    description=(
        "Bards are versatile performers who weave magic through music, story, "
        "and force of personality. Masters of inspiration and manipulation, they "
        "bolster allies, debilitate foes, and uncover secrets hidden from lesser "
        "minds. Their broad talents and lore make them invaluable — though they "
        "rarely excel at any one thing as much as a specialist would."
    ),
    level_progression=PROGRESSION,
    prime_attribute=Ability.CHA,
    multi_class_requirements={Ability.CHA: 14},
    min_remort=2,
)

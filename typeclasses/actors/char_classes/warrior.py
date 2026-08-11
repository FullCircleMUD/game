from enums.abilities_enum import Ability
from typeclasses.actors.char_classes.char_class_base import CharClassBase
from commands.class_skill_cmdsets.cmdset_warrior import CmdSetWarrior


PROGRESSION = {
    # Early Levels (1-10) - Learning the basics
    1: {"weapon_skill_pts": 4, "class_skill_pts": 3, "general_skill_pts": 2, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    2: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    3: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    4: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    5: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:11                class:8                 general:3           hp:60        mana:10        move:25

    6: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    7: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    8: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    9: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    10: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:19                class:14                general:5           hp:110      mana:20         move:50

    11: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    12: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    13: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    14: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    15: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:28                class:20                general:6           hp:160      mana:30         move:75

    16: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    17: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    18: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    19: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    20: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:36                class:26                general:8           hp:210      mana:40         move:100

    21: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    22: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    23: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    24: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    25: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:45                class:32                general:10          hp:260      mana:50         move:125

    # High Levels (26-40) - Master warrior
    26: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    27: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    28: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    29: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    30: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:55                class:28                general:11        hp:310        mana:60         move:150

    31: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    32: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    33: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    34: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    35: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:65                 class:44                general:13         hp:360        mana:70        move:175

    36: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    37: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    38: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    39: {"weapon_skill_pts": 2, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    40: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 10, "mana_gain": 2, "move_gain": 5},
    #  Total       weapon:75                 class:50              general:16          hp:410       mana:80         move:200
    #   weapon  gm in 3 / gm in 2 + master in 1 + expert in 1 / master in 4 + expert in 1 / expert in 8
    #   class   gm in 2 / master in 3 / expert in 5
    #   general master in 1 / expert in 1 skilled in 1
    #   weak strong in weapons - mid in class - weak in general

    # mage      12/82/41 = 135
    # warrior   75/50/16 = 141
    # thief     41/50/50 = 141
    # cleric.   41/70/25 = 136

}


WARRIOR = CharClassBase(
    key="warrior",
    display_name="Warrior",
    description=(
        "Warriors are masters of combat and warfare. They excel with all manner "
        "of weapons and armor, forming the backbone of any adventuring party. "
        "Their extensive weapon training comes at the cost of limited magical "
        "knowledge and general skills."
    ),
    level_progression=PROGRESSION,
    prime_attribute=Ability.STR,
    multi_class_requirements={Ability.STR: 14, Ability.CON: 12},
    class_cmdset=CmdSetWarrior,
)

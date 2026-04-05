from enums.abilities_enum import Ability
from typeclasses.actors.char_classes.char_class_base import CharClassBase
from commands.class_skill_cmdsets.cmdset_cleric import CmdSetCleric


PROGRESSION = {
    # Early Levels (1-10) - Learning the basics
    1: {"weapon_skill_pts": 2, "class_skill_pts": 3, "general_skill_pts": 2, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    2: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    3: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    4: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    5: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:6   class:11  general:4   hp:40   mana:30  move:20

    6: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    7: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    8: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    9: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    10: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:11  class:21  general:7   hp:80   mana:60  move:40

    11: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    12: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    13: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    14: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    15: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:16  class:31  general:9   hp:120  mana:90  move:60

    16: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    17: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    18: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    19: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    20: {"weapon_skill_pts": 1, "class_skill_pts": 3, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:21  class:42  general:12  hp:160  mana:120 move:80

    21: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    22: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    23: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    24: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    25: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:26  class:52  general:14  hp:200  mana:150 move:100

    # High Levels (26-40) - Master cleric
    26: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    27: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    28: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    29: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    30: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:31  class:62  general:17  hp:240  mana:180 move:120

    31: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    32: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    33: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    34: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    35: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:36  class:72  general:19  hp:280  mana:210 move:140

    36: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    37: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    38: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    39: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    40: {"weapon_skill_pts": 1, "class_skill_pts": 3, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 6, "move_gain": 4},
    #  Total       weapon:41  class:83  general:22  hp:320  mana:240 move:160
}


CLERIC = CharClassBase(
    key="cleric",
    display_name="Cleric",
    description=(
        "Clerics are divine servants who channel the power of their faith to "
        "heal allies, smite enemies, and protect the faithful. They command "
        "five sacred domains — from the restorative art of divine healing to "
        "the commanding force of divine dominion. Hardier than mages and able "
        "to wield maces and hammers, they serve as the spiritual backbone of "
        "any adventuring party."
    ),
    level_progression=PROGRESSION,
    prime_attribute=Ability.WIS,
    multi_class_requirements={Ability.WIS: 14},
    class_cmdset=CmdSetCleric,
    grants_spells=True,
)

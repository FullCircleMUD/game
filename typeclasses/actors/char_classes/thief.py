from enums.abilities_enum import Ability
from typeclasses.actors.char_classes.char_class_base import CharClassBase
from commands.class_skill_cmdsets.cmdset_thief import CmdSetThief


PROGRESSION = {
    # Early Levels (1-10) - Learning the basics
    1: {"weapon_skill_pts": 2, "class_skill_pts": 3, "general_skill_pts": 3, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    2: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    3: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    4: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    5: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:6                 class:7                 general:7        hp:32          mana:20         move:20

    6: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    7: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    8: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    9: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    10: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:11                class:12                general:12       hp:62           mana:40        move:40

    11: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    12: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    13: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    14: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    15: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:16                class:17                general:17        hp:92         mana:60         move:60

    16: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    17: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    18: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    19: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    20: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:21                class:22                general:22      hp:122          mana:80         move:80

    21: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    22: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    23: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    24: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    25: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:26                class:27                general:27          hp:152          mana:100        move:100

    26: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    27: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    28: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    29: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    30: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:31                class:32                general:32          hp:182          mana:120        move:120

    31: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    32: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    33: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    34: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    35: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:36                class:40                general:40        hp:212          mana:140        move:140

    36: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    37: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    38: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    39: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    40: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 2, "hp_gain": 6, "mana_gain": 4, "move_gain": 4},
    #  Total       weapon:41                class:50                general:50         hp:242          mana:160        move:160

    #   weapon    gm at 1 + master at 1 / master at 2 expert at 1 / expert at 4
    #   class     gm at 2 / master at 3 / expert at 5
    #   general   gm at 2 / master at 3 / expert at 5
    #   mid in weapons - mid in class - mid in general

    # mage      12/82/41 = 135
    # warrior   75/50/16 = 141
    # thief     41/50/50 = 141
    # cleric.   41/70/25 = 136

}


THIEF = CharClassBase(
    key="thief",
    display_name="Thief",
    description=(
        "Thieves are versatile adventurers who rely on skill, cunning, and "
        "stealth rather than brute force. They excel in a wide variety of "
        "abilities from lockpicking to stabbing from the shadows, making them invaluable "
        "for overcoming obstacles and gathering information."
    ),
    level_progression=PROGRESSION,
    prime_attribute=Ability.DEX,
    multi_class_requirements={Ability.DEX: 14},
    class_cmdset=CmdSetThief,
)

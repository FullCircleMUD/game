from enums.abilities_enum import Ability
from typeclasses.actors.char_classes.char_class_base import CharClassBase
from commands.class_skill_cmdsets.cmdset_mage import CmdSetMage


PROGRESSION = {
    # Early Levels (1-10) - Learning the basics
    1: {"weapon_skill_pts": 1, "class_skill_pts": 4, "general_skill_pts": 2, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    2: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    3: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    4: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    5: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:2                 class:12                general:6       hp:20           mana:40         move:15

    6: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    7: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    8: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    9: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    10: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:4                 class:22                general:11         hp:40        mana:80         move:30

    11: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    12: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    13: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    14: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    15: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:5                 class:32                general:16        hp:60         mana:120        move:45

    16: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    17: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    18: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    19: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    20: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:7                 class:42                general:21         hp:80        mana:160        move:60

    21: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    22: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    23: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    24: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    25: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:8                 class:52                general:26       hp:100         mana:200        move:75

    # High Levels (26-40) - Master mage
    26: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    27: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    28: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    29: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    30: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:9                 class:62  g             eneral:31       hp:120          mana:240        move:90

    31: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    32: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    33: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    34: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    35: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:10                class:72                general:36      hp:140          mana:280        move:105

    36: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    37: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    38: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    39: {"weapon_skill_pts": 0, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    40: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 4, "mana_gain": 8, "move_gain": 3},
    #  Total       weapon:12                class:82                general:41      hp:160          mana:320        move:120
    #   weapon 1 expert + 1 skilled
    #   class  gm in 3 + skilled in 1 / master in 5 / expert in 9 / skilled in 20
    #   general  GM in 1 + master in 1 / master in 2 + expert in 1 / expert in 4 / skilled in 10
    #   weak in weapons - strong in class - mid in general


    # mage      12/82/41 = 135
    # warrior   75/50/16 = 141
    # thief     41/50/50 = 141
    # cleric.   41/70/25 = 136


}


MAGE = CharClassBase(
    key="mage",
    display_name="Mage",
    description=(
        "Mages are scholars of the arcane arts, wielding devastating magical "
        "power at the cost of physical frailty. They command seven schools of "
        "magic — from the destructive force of evocation to the subtle art of "
        "illusion — learning spells by transcribing ancient scrolls into their "
        "spellbooks. What they lack in martial prowess, they more than make up "
        "for in raw magical might."
    ),
    level_progression=PROGRESSION,
    prime_attribute=Ability.INT,
    multi_class_requirements={Ability.INT: 14},
    class_cmdset=CmdSetMage,
)

from enums.abilities_enum import Ability
from enums.alignment import Alignment
from typeclasses.actors.char_classes.char_class_base import CharClassBase


PROGRESSION = {
    # Early Levels (1-10) - Learning the basics
    1: {"weapon_skill_pts": 3, "class_skill_pts": 3, "general_skill_pts": 2, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    2: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    3: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    4: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    5: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:9   class:9   general:4   hp:40   mana:20  move:25

    6: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    7: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    8: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    9: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    10: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:17  class:17  general:6   hp:80   mana:40  move:50

    11: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    12: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    13: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    14: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    15: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:25  class:25  general:8   hp:120  mana:60  move:75

    16: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    17: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    18: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    19: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    20: {"weapon_skill_pts": 1, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:32  class:33  general:10  hp:160  mana:80  move:100

    21: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    22: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    23: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    24: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    25: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:40  class:41  general:12  hp:200  mana:100 move:125

    # High Levels (26-40) - Master paladin
    26: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    27: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    28: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    29: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    30: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:48  class:49  general:14  hp:240  mana:120 move:150

    31: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    32: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    33: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    34: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    35: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:56  class:57  general:16  hp:280  mana:140 move:175

    36: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    37: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    38: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    39: {"weapon_skill_pts": 1, "class_skill_pts": 1, "general_skill_pts": 0, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    40: {"weapon_skill_pts": 2, "class_skill_pts": 2, "general_skill_pts": 1, "hp_gain": 8, "mana_gain": 4, "move_gain": 5},
    #  Total       weapon:65  class:66  general:18  hp:320  mana:160 move:200
}


PALADIN = CharClassBase(
    key="paladin",
    display_name="Paladin",
    description=(
        "Paladins are holy warriors who blend martial prowess with divine magic. "
        "Drawing power from an unwavering oath, they command both blade and prayer "
        "with equal conviction. They share the cleric's five sacred domains and "
        "the warrior's combat techniques, though mastering both paths demands "
        "more lifetimes than one."
    ),
    level_progression=PROGRESSION,
    prime_attribute=Ability.CHA,
    multi_class_requirements={Ability.STR: 14, Ability.CHA: 14},
    excluded_alignments=[
        Alignment.LAWFUL_EVIL,
        Alignment.NEUTRAL_EVIL,
        Alignment.CHAOTIC_EVIL,
    ],
    grants_spells=True,
    min_remort=1,
)

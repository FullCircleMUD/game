"""
Mastery-scaled potion effect tables.

Maps prototype_key → {"named_effect_key": str, mastery_int: {"effects": [...], "duration": int}}

At brew time, cmd_craft looks up the brewer's alchemy mastery and sets the
potion's effects/duration from these tables. Kept separate from prototype
dicts so Evennia's spawn() doesn't store the tables as item attributes.

named_effect_key is used by PotionNFTItem for anti-stacking — any two potions
sharing the same key (e.g. "potion_strength") can't stack.

Mastery levels: 1=BASIC, 2=SKILLED, 3=EXPERT, 4=MASTER, 5=GRANDMASTER
"""

POTION_SCALING = {
    # ── Stat bonus potions ────────────────────────────────────────────
    "the_bull": {
        "named_effect_key": "potion_strength",
        1: {"effects": [{"type": "stat_bonus", "stat": "strength", "value": 1}], "duration": 60},
        2: {"effects": [{"type": "stat_bonus", "stat": "strength", "value": 2}], "duration": 120},
        3: {"effects": [{"type": "stat_bonus", "stat": "strength", "value": 3}], "duration": 180},
        4: {"effects": [{"type": "stat_bonus", "stat": "strength", "value": 4}], "duration": 240},
        5: {"effects": [{"type": "stat_bonus", "stat": "strength", "value": 5}], "duration": 300},
    },
    "cats_grace": {
        "named_effect_key": "potion_dexterity",
        1: {"effects": [{"type": "stat_bonus", "stat": "dexterity", "value": 1}], "duration": 60},
        2: {"effects": [{"type": "stat_bonus", "stat": "dexterity", "value": 2}], "duration": 120},
        3: {"effects": [{"type": "stat_bonus", "stat": "dexterity", "value": 3}], "duration": 180},
        4: {"effects": [{"type": "stat_bonus", "stat": "dexterity", "value": 4}], "duration": 240},
        5: {"effects": [{"type": "stat_bonus", "stat": "dexterity", "value": 5}], "duration": 300},
    },
    "the_bear": {
        "named_effect_key": "potion_constitution",
        1: {"effects": [{"type": "stat_bonus", "stat": "constitution", "value": 1}], "duration": 60},
        2: {"effects": [{"type": "stat_bonus", "stat": "constitution", "value": 2}], "duration": 120},
        3: {"effects": [{"type": "stat_bonus", "stat": "constitution", "value": 3}], "duration": 180},
        4: {"effects": [{"type": "stat_bonus", "stat": "constitution", "value": 4}], "duration": 240},
        5: {"effects": [{"type": "stat_bonus", "stat": "constitution", "value": 5}], "duration": 300},
    },
    "foxs_cunning": {
        "named_effect_key": "potion_intelligence",
        1: {"effects": [{"type": "stat_bonus", "stat": "intelligence", "value": 1}], "duration": 60},
        2: {"effects": [{"type": "stat_bonus", "stat": "intelligence", "value": 2}], "duration": 120},
        3: {"effects": [{"type": "stat_bonus", "stat": "intelligence", "value": 3}], "duration": 180},
        4: {"effects": [{"type": "stat_bonus", "stat": "intelligence", "value": 4}], "duration": 240},
        5: {"effects": [{"type": "stat_bonus", "stat": "intelligence", "value": 5}], "duration": 300},
    },
    "owls_insight": {
        "named_effect_key": "potion_wisdom",
        1: {"effects": [{"type": "stat_bonus", "stat": "wisdom", "value": 1}], "duration": 60},
        2: {"effects": [{"type": "stat_bonus", "stat": "wisdom", "value": 2}], "duration": 120},
        3: {"effects": [{"type": "stat_bonus", "stat": "wisdom", "value": 3}], "duration": 180},
        4: {"effects": [{"type": "stat_bonus", "stat": "wisdom", "value": 4}], "duration": 240},
        5: {"effects": [{"type": "stat_bonus", "stat": "wisdom", "value": 5}], "duration": 300},
    },
    "silver_tongue": {
        "named_effect_key": "potion_charisma",
        1: {"effects": [{"type": "stat_bonus", "stat": "charisma", "value": 1}], "duration": 60},
        2: {"effects": [{"type": "stat_bonus", "stat": "charisma", "value": 2}], "duration": 120},
        3: {"effects": [{"type": "stat_bonus", "stat": "charisma", "value": 3}], "duration": 180},
        4: {"effects": [{"type": "stat_bonus", "stat": "charisma", "value": 4}], "duration": 240},
        5: {"effects": [{"type": "stat_bonus", "stat": "charisma", "value": 5}], "duration": 300},
    },

    # ── Restore potions ───────────────────────────────────────────────
    "lifes_essence": {
        1: {"effects": [{"type": "restore", "stat": "hp", "dice": "2d4+1"}], "duration": 0},
        2: {"effects": [{"type": "restore", "stat": "hp", "dice": "4d4+2"}], "duration": 0},
        3: {"effects": [{"type": "restore", "stat": "hp", "dice": "6d4+3"}], "duration": 0},
        4: {"effects": [{"type": "restore", "stat": "hp", "dice": "8d4+4"}], "duration": 0},
        5: {"effects": [{"type": "restore", "stat": "hp", "dice": "10d4+5"}], "duration": 0},
    },
    "the_wellspring": {
        1: {"effects": [{"type": "restore", "stat": "mana", "dice": "2d4+1"}], "duration": 0},
        2: {"effects": [{"type": "restore", "stat": "mana", "dice": "4d4+2"}], "duration": 0},
        3: {"effects": [{"type": "restore", "stat": "mana", "dice": "6d4+3"}], "duration": 0},
        4: {"effects": [{"type": "restore", "stat": "mana", "dice": "8d4+4"}], "duration": 0},
        5: {"effects": [{"type": "restore", "stat": "mana", "dice": "10d4+5"}], "duration": 0},
    },
    "the_zephyr": {
        1: {"effects": [{"type": "restore", "stat": "move", "dice": "2d4+1"}], "duration": 0},
        2: {"effects": [{"type": "restore", "stat": "move", "dice": "4d4+2"}], "duration": 0},
        3: {"effects": [{"type": "restore", "stat": "move", "dice": "6d4+3"}], "duration": 0},
        4: {"effects": [{"type": "restore", "stat": "move", "dice": "8d4+4"}], "duration": 0},
        5: {"effects": [{"type": "restore", "stat": "move", "dice": "10d4+5"}], "duration": 0},
    },
}


def get_scaling(prototype_key):
    """Look up scaling data for a prototype. Returns None if not scaled."""
    return POTION_SCALING.get(prototype_key)

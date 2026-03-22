"""
Gem enchantment roll tables.

Maps gem type → mastery level → d100 roll table for probabilistic enchanting.
Each table entry is a ("range", value) tuple compatible with
DiceRoller.roll_random_table().

A separate restriction table determines whether the enchanted gem gets
race/class restrictions.

Tables are designed to be easily edited for playtesting and balance.
Higher mastery levels will shift probabilities toward better outcomes
(future — only BASIC ruby table implemented for POC).

Mastery levels: 1=BASIC, 2=SKILLED, 3=EXPERT, 4=MASTER, 5=GRANDMASTER
"""

import random

from typeclasses.actors.char_classes import get_available_char_classes
from typeclasses.actors.races import get_available_races
from utils.dice_roller import dice


# ── Ruby enchantment tables (keyed by mastery level) ──────────────────

RUBY_ENCHANT_TABLE = {
    1: (  # BASIC
        ("1-10",  [{"type": "stat_bonus", "stat": "initiative_bonus", "value": 1}]),
        ("11-20", [{"type": "stat_bonus", "stat": "stealth_bonus", "value": 1}]),
        ("21-30", [{"type": "stat_bonus", "stat": "perception_bonus", "value": 1}]),
        ("31-40", [{"type": "condition", "condition": "detect_invis"}]),
        ("41-50", [{"type": "condition", "condition": "darkvision"}]),
        ("51-60", [{"type": "condition", "condition": "fly"}]),
        ("61-70", [{"type": "condition", "condition": "water_breathing"}]),
        ("71-80", [{"type": "condition", "condition": "blessed"}]),
        ("81-90", [{"type": "condition", "condition": "alert"}]),
        ("91-100", [
            {"type": "stat_bonus", "stat": "total_hit_bonus", "value": 1},
            {"type": "stat_bonus", "stat": "total_damage_bonus", "value": 1},
        ]),
    ),
}

# ── Restriction table (shared across all gem types) ───────────────────

RESTRICTION_TABLE = (
    ("1-20",   "race"),
    ("21-50",  "class"),
    ("51-100", "none"),
)

# ── Lookup map: output_table key → enchant table ─────────────────────

_ENCHANT_TABLES = {
    "enchanted_ruby": RUBY_ENCHANT_TABLE,
}


def roll_gem_enchantment(table_key, mastery_level):
    """
    Roll on a gem enchantment table and restriction table.

    Uses DiceRoller.roll_random_table() for consistent dice logic.

    Args:
        table_key: Lookup key (e.g. "enchanted_ruby") matching _ENCHANT_TABLES.
        mastery_level: Integer mastery level (1-5).

    Returns:
        (effects, restrictions) tuple where:
        - effects: list of effect dicts (same format as wear_effects)
        - restrictions: dict with optional "required_races" or "required_classes"
    """
    enchant_table = _ENCHANT_TABLES.get(table_key)
    if not enchant_table:
        raise ValueError(f"Unknown gem enchant table: {table_key}")

    # Use the highest available mastery table (fall back if table not defined)
    level_table = None
    for lvl in range(mastery_level, 0, -1):
        if lvl in enchant_table:
            level_table = enchant_table[lvl]
            break
    if not level_table:
        raise ValueError(
            f"No table defined for {table_key} at mastery {mastery_level}"
        )

    # Roll effects via DiceRoller
    effects = dice.roll_random_table("1d100", level_table)

    # Roll restrictions via DiceRoller
    restriction_type = dice.roll_random_table("1d100", RESTRICTION_TABLE)

    restrictions = {}
    if restriction_type == "race":
        non_remort_races = list(get_available_races(0).keys())
        if non_remort_races:
            restrictions["required_races"] = [random.choice(non_remort_races)]
    elif restriction_type == "class":
        base_classes = list(get_available_char_classes(0).keys())
        if base_classes:
            restrictions["required_classes"] = [random.choice(base_classes)]

    return effects, restrictions

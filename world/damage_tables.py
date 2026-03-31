"""
Weapon damage lookup tables — material tier + mastery level = damage dice.

See design/WEAPON_DAMAGE_SCALING.md for the full design rationale.

Usage:
    from world.damage_tables import get_damage_dice
    dice_str = get_damage_dice("d8", "iron", MasteryLevel.BASIC)  # "1d8"
"""

from enums.mastery_level import MasteryLevel

U = MasteryLevel.UNSKILLED
B = MasteryLevel.BASIC
S = MasteryLevel.SKILLED
E = MasteryLevel.EXPERT
M = MasteryLevel.MASTER
G = MasteryLevel.GRANDMASTER

DAMAGE_TABLES = {
    # ── d1 Base (Blowgun, Bola — fixed 1 damage regardless of material/mastery) ──
    "d1": {
        "wood":       {U: "1", B: "1", S: "1", E: "1", M: "1", G: "1"},
        "bronze":     {U: "1", B: "1", S: "1", E: "1", M: "1", G: "1"},
        "iron":       {U: "1", B: "1", S: "1", E: "1", M: "1", G: "1"},
        "steel":      {U: "1", B: "1", S: "1", E: "1", M: "1", G: "1"},
        "adamantine": {U: "1", B: "1", S: "1", E: "1", M: "1", G: "1"},
    },
    # ── d4 Base (Dagger, Shuriken) ──
    "d4": {
        "wood":       {U: "1",   B: "1d2", S: "1d3", E: "1d4", M: "1d5", G: "2d3"},
        "bronze":     {U: "1",   B: "1d3", S: "1d4", E: "1d5", M: "1d6", G: "2d3"},
        "iron":       {U: "1d2", B: "1d4", S: "1d5", E: "1d6", M: "1d7", G: "2d4"},
        "steel":      {U: "1d2", B: "1d5", S: "1d6", E: "1d7", M: "2d4", G: "2d5"},
        "adamantine": {U: "1d3", B: "1d6", S: "1d7", E: "2d4", M: "2d5", G: "2d6"},
    },
    # ── d6 Base (Shortsword, Handaxe, Sai, Nunchaku) ──
    "d6": {
        "wood":       {U: "1d2", B: "1d4", S: "1d5", E: "1d6", M: "1d7", G: "2d4"},
        "bronze":     {U: "1d2", B: "1d5", S: "1d6", E: "1d7", M: "2d4", G: "2d5"},
        "iron":       {U: "1d3", B: "1d6", S: "1d7", E: "2d4", M: "2d5", G: "2d6"},
        "steel":      {U: "1d3", B: "1d7", S: "2d4", E: "2d5", M: "2d6", G: "2d7"},
        "adamantine": {U: "1d4", B: "2d4", S: "2d5", E: "2d6", M: "2d7", G: "4d4"},
    },
    # ── d8 Base (Longsword, Rapier, Mace, Spear, Staff, Bow, Crossbow, Lance, Ninjato) ──
    "d8": {
        "wood":       {U: "1d3", B: "1d6", S: "1d7", E: "1d8", M: "1d10", G: "2d6"},
        "bronze":     {U: "1d3", B: "1d7", S: "1d8", E: "1d10", M: "2d6", G: "2d7"},
        "iron":       {U: "1d4", B: "1d8", S: "1d10", E: "2d6", M: "2d7", G: "2d8"},
        "steel":      {U: "1d5", B: "1d10", S: "2d6", E: "2d7", M: "2d8", G: "2d10"},
        "adamantine": {U: "1d6", B: "2d6", S: "2d7", E: "2d8", M: "2d10", G: "4d6"},
    },
    # ── d10 Base (Greatclub, Battleaxe) ──
    "d10": {
        "wood":       {U: "1d3", B: "1d7", S: "1d8", E: "1d10", M: "1d12", G: "2d7"},
        "bronze":     {U: "1d4", B: "1d8", S: "1d10", E: "1d12", M: "2d7", G: "2d8"},
        "iron":       {U: "1d5", B: "1d10", S: "1d12", E: "2d7", M: "2d8", G: "2d10"},
        "steel":      {U: "1d6", B: "1d12", S: "2d7", E: "2d8", M: "2d10", G: "2d12"},
        "adamantine": {U: "1d7", B: "2d7", S: "2d8", E: "2d10", M: "2d12", G: "4d7"},
    },
    # ── d12 Base (Greataxe) ──
    "d12": {
        "wood":       {U: "1d4", B: "1d8", S: "1d10", E: "1d12", M: "2d7", G: "2d8"},
        "bronze":     {U: "1d5", B: "1d10", S: "1d12", E: "2d7", M: "2d8", G: "2d10"},
        "iron":       {U: "1d6", B: "1d12", S: "2d7", E: "2d8", M: "2d10", G: "2d12"},
        "steel":      {U: "1d7", B: "2d7", S: "2d8", E: "2d10", M: "2d12", G: "4d7"},
        "adamantine": {U: "1d8", B: "2d8", S: "2d10", E: "2d12", M: "4d7", G: "4d8"},
    },
    # ── 2d6 Base (Greatsword) ──
    "2d6": {
        "wood":       {U: "1d4", B: "2d4", S: "2d5", E: "2d6", M: "2d7", G: "4d4"},
        "bronze":     {U: "1d5", B: "2d5", S: "2d6", E: "2d7", M: "4d4", G: "4d5"},
        "iron":       {U: "1d6", B: "2d6", S: "2d7", E: "4d4", M: "4d5", G: "4d6"},
        "steel":      {U: "1d7", B: "2d7", S: "4d4", E: "4d5", M: "4d6", G: "4d7"},
        "adamantine": {U: "2d4", B: "4d4", S: "4d5", E: "4d6", M: "4d7", G: "8d4"},
    },
    # ── 2d7 Base (Lance — mounted cavalry weapon) ──
    "2d7": {
        "wood":       {U: "1d5", B: "2d5", S: "2d6", E: "2d7", M: "2d8", G: "4d5"},
        "bronze":     {U: "1d6", B: "2d6", S: "2d7", E: "2d8", M: "4d5", G: "4d6"},
        "iron":       {U: "1d7", B: "2d7", S: "2d8", E: "4d5", M: "4d6", G: "4d7"},
        "steel":      {U: "2d4", B: "2d8", S: "4d5", E: "4d6", M: "4d7", G: "4d8"},
        "adamantine": {U: "2d5", B: "4d5", S: "4d6", E: "4d7", M: "4d8", G: "8d5"},
    },
}


def get_damage_dice(base_damage, material, mastery):
    """Resolve damage dice string from base die, material, and wielder mastery.

    Args:
        base_damage: str — "d1", "d4", "d6", "d8", "d10", "d12", "2d6", or "2d7"
        material: str — "wood", "bronze", "iron", "steel", or "adamantine"
        mastery: MasteryLevel enum value

    Returns:
        Damage dice string like "1d8" or "2d6".

    Raises:
        KeyError if base_damage or material is not in the table.
    """
    return DAMAGE_TABLES[base_damage][material][mastery]

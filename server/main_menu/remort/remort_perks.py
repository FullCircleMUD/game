"""
Remort perk definitions — data-driven registry.

Each perk is a dict describing what it does. The remort command reads this
list to present options and apply the chosen perk.

To add a new perk, just add another dict to the list. No code changes needed.

Fields:
    key         — unique identifier
    name        — display name shown to the player
    desc        — one-line description
    attribute   — the AttributeProperty on FCMCharacter to modify
    increment   — how much to add per take
    cap         — absolute maximum value for the attribute (perk hidden at cap)
"""

POINT_BUY_CAP = 75  # cost of 18,18,18,16,12,10

REMORT_PERKS = [
    {
        "key": "bonus_point_buy",
        "name": "Enhanced Abilities",
        "desc": "+5 to your ability score point buy budget (permanent)",
        "attribute": "point_buy",
        "increment": 5,
        "cap": POINT_BUY_CAP,
    },
    {
        "key": "bonus_hp_per_level",
        "name": "Vitality",
        "desc": "+1 HP per character level (permanent)",
        "attribute": "bonus_hp_per_level",
        "increment": 1,
        "cap": 5,
    },
    {
        "key": "bonus_mana_per_level",
        "name": "Arcane Fortitude",
        "desc": "+1 mana per character level (permanent)",
        "attribute": "bonus_mana_per_level",
        "increment": 1,
        "cap": 5,
    },
    {
        "key": "bonus_move_per_level",
        "name": "Endurance",
        "desc": "+1 move per character level (permanent)",
        "attribute": "bonus_move_per_level",
        "increment": 1,
        "cap": 5,
    },
    {
        "key": "bonus_weapon_skill_pts",
        "name": "Martial Training",
        "desc": "+10 weapon skill points at character creation (permanent)",
        "attribute": "bonus_weapon_skill_pts",
        "increment": 10,
        "cap": 50,
    },
    {
        "key": "bonus_class_skill_pts",
        "name": "Vocational Mastery",
        "desc": "+10 class skill points at character creation (permanent)",
        "attribute": "bonus_class_skill_pts",
        "increment": 10,
        "cap": 50,
    },
    {
        "key": "bonus_general_skill_pts",
        "name": "Worldly Experience",
        "desc": "+10 general skill points at character creation (permanent)",
        "attribute": "bonus_general_skill_pts",
        "increment": 10,
        "cap": 50,
    },
]


def get_available_perks(character):
    """Return list of perks the character hasn't capped yet."""
    available = []
    for perk in REMORT_PERKS:
        current = getattr(character, perk["attribute"], 0)
        if current < perk["cap"]:
            available.append(perk)
    return available


def apply_perk(character, perk):
    """Apply a perk to the character. Returns (success, message)."""
    current = getattr(character, perk["attribute"], 0)
    if current >= perk["cap"]:
        return False, f"{perk['name']} is already at maximum."

    new_value = min(current + perk["increment"], perk["cap"])
    setattr(character, perk["attribute"], new_value)
    return True, f"|g{perk['name']}|n applied! {perk['attribute']}: {current} → {new_value}"

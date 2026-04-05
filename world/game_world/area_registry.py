"""
Area registry — static metadata for the `areas` command.

Each entry describes a district within a zone, including its level
range, location relative to its zone hub, and optional notes. Add
new entries as zones and districts are built.
"""

AREA_REGISTRY = [
    # ── Millholm ──────────────────────────────────────────────────
    {
        "zone": "Millholm",
        "district": "Town",
        "levels": "All",
        "location": "Hub — shops, guilds, bank, inn",
        "notes": "",
    },
    {
        "zone": "Millholm",
        "district": "Farms",
        "levels": "1",
        "location": "West of town",
        "notes": "Wheat, mills, cotton",
    },
    {
        "zone": "Millholm",
        "district": "Woods",
        "levels": "1-2",
        "location": "East of town",
        "notes": "Sawmill, smelter",
    },
    {
        "zone": "Millholm",
        "district": "Sewers",
        "levels": "1",
        "location": "Beneath town (hidden)",
        "notes": "Thieves' Lair",
    },
    {
        "zone": "Millholm",
        "district": "Cemetery",
        "levels": "3",
        "location": "North-east of town",
        "notes": "",
    },
    {
        "zone": "Millholm",
        "district": "Mine",
        "levels": "2-3",
        "location": "Past the deep woods",
        "notes": "Kobolds",
    },
    {
        "zone": "Millholm",
        "district": "Rooftops",
        "levels": "3-4",
        "location": "Above the craft quarter",
        "notes": "",
    },
    {
        "zone": "Millholm",
        "district": "Southern District",
        "levels": "4-5",
        "location": "South of town",
        "notes": "Gnolls, barrow",
    },
    {
        "zone": "Millholm",
        "district": "Faerie Hollow",
        "levels": "?",
        "location": "Hidden in the deep woods",
        "notes": "Arcane dust",
    },
]

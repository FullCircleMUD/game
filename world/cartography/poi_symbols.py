"""
Central POI symbol registry — single source of truth for all district maps.

Change a symbol here and every map updates on next render.
Maps reference POI types by string key; render_map() looks up the
display character from this module at render time.
"""

# POI type → single display character
POI_SYMBOLS = {
    "road":        "#",
    "gate":        "@",
    "cemetery":    "C",
    "inn":         "I",
    "smithy":      "S",
    "bank":        "$",
    "temple":      "+",
    "guild":       "G",
    "gaol":        "g",
    "shop":        "*",
    "bakery":      "B",
    "stable":      "H",
    "woodshop":    "W",
    "tailor":      "T",
    "leathershop": "L",
    "apothecary":  "A",
    "jeweller":    "J",
    "post_office": "P",
    "house":       "h",
    "distillery":  "D",
    "crossroads":  "X",
    "zone_exit":   "X",
    # Underground / dungeon
    "tunnel":      "~",
    "chamber":     "O",
    "shaft":       "v",
    "dead_end":    "x",
    "mine":        "m",
    "lair":        "!",
    # Region overview
    "town":        "T",
    "farm":        "F",
    "woods":       "W",
    "district":    "d",
    "unknown":     "?",
}

# POI type → legend display name
POI_NAMES = {
    "road":        "Road",
    "gate":        "Gate",
    "cemetery":    "Cemetery",
    "inn":         "Inn",
    "smithy":      "Smithy",
    "bank":        "Bank",
    "temple":      "Temple",
    "guild":       "Guild",
    "gaol":        "Gaol",
    "shop":        "Shop",
    "bakery":      "Bakery",
    "stable":      "Stable",
    "woodshop":    "Woodshop",
    "tailor":      "Tailor",
    "leathershop": "Leathershop",
    "apothecary":  "Apothecary",
    "jeweller":    "Jeweller",
    "post_office": "Post Office",
    "house":       "House",
    "distillery":  "Distillery",
    "crossroads":  "Crossroads",
    "zone_exit":   "Map Exit",
    "tunnel":      "Tunnel",
    "chamber":     "Chamber",
    "shaft":       "Shaft",
    "dead_end":    "Dead End",
    "mine":        "Mine",
    "lair":        "Lair",
    "town":        "Town",
    "farm":        "Farm",
    "woods":       "Woods",
    "district":    "District",
    "unknown":     "Unknown",
}

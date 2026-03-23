"""
Central POI symbol registry — single source of truth for all district maps.

Change a symbol here and every map updates on next render.
Maps reference POI types by string key; render_map() looks up the
display character from this module at render time.
"""

# POI type → single display character
POI_SYMBOLS = {
    "road":        "#",
    "gate":        "G",
    "cemetery":    "c",
    "inn":         "I",
    "tavern":      "T",
    "smithy":      "S",
    "bank":        "$",
    "temple":      "+",
    "guild":       "g",
    "shop":        "*",
    "market":      "M",
    "bakery":      "B",
    "stable":      "H",
    "woodshop":    "W",
    "tailor":      "L",
    "leathershop": "l",
    "apothecary":  "A",
    "jeweller":    "J",
    "post_office": "P",
    "house":       "h",
    "distillery":  "D",
    "square":      "o",
    "crossroads":  "X",
    "zone_exit":   ">",
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
    "tavern":      "Tavern",
    "smithy":      "Smithy",
    "bank":        "Bank",
    "temple":      "Temple",
    "guild":       "Guild",
    "shop":        "Shop",
    "market":      "Market",
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
    "square":      "Square",
    "crossroads":  "Crossroads",
    "zone_exit":   "Zone Exit",
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

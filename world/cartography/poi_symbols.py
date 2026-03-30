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
    "bank":        "$",
    "temple":      "+",
    "guild":       "G",
    "gaol":        "g",
    "shop":        "S",
    "smithy":      "s",
    "workshop":    "W",
    "bakery":      "B",
    "stable":      "H",
    "post_office": "P",
    "house":       "h",
    "lake":        "L",
    "zone_exit":   "X",
    # Underground / dungeon
    "chamber":     "O",
    "shaft":       "v",
    "dead_end":    "x",
    "mine":        "m",
    "lair":        "!",
    # Region overview
    "town":            "T",
    "farm":            "F",
    "woods":           "W",
    "district":        "d",
    "unknown":         "?",
    "resource_processing": "R",
    "region_mine":     "M",
    "region_dungeon":  "D",
    "zone_boundary":   "Z",
}

# POI type → legend display name
POI_NAMES = {
    "road":        "Road",
    "gate":        "Gate",
    "cemetery":    "Cemetery",
    "inn":         "Inn",
    "bank":        "Bank",
    "temple":      "Temple",
    "guild":       "Guild",
    "gaol":        "Gaol",
    "shop":        "Shop",
    "smithy":      "Smithy",
    "workshop":    "Workshop",
    "bakery":      "Bakery",
    "stable":      "Stable",
    "post_office": "Post Office",
    "house":       "House",
    "lake":        "Lake",
    "zone_exit":   "Map Exit",
    # Underground / dungeon
    "chamber":     "Chamber",
    "shaft":       "Shaft",
    "dead_end":    "Dead End",
    "mine":        "Mine",
    "lair":        "Lair",
    # Region overview
    "town":            "Town",
    "farm":            "Farm",
    "woods":           "Woods",
    "district":            "District",
    "unknown":             "Unknown",
    "resource_processing": "Processing",
    "region_mine":         "Mine",
    "region_dungeon":      "Dungeon",
    "zone_boundary":       "Zone Exit",
}

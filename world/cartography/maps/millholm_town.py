"""
Millholm Town district map.

Template: streets, road segments, shops, landmarks.
NOT included: building interiors, private spaces, the secret passage,
NPC back rooms (hendricks_house, mara_house, priest_quarters, etc.).

Point key → room tag convention:
    room.tags.add("millholm_town:<point_key>", category="map_cell")

Layout: The Old Trade Way runs E-W across the middle. Shops branch
north and south off the road. The 3x3 market square is rendered as
road intersections (not a separate POI type). Cemetery to the north,
Southern District gate to the south.

            col: 0   4   8  12  16  20  24  28  32
"""

from world.cartography.map_registry import register_map

#                 0123456789012345678901234567890123456
_TEMPLATE = (    #0         1         2         3
    "                .                \n"  # row 0:  cemetery
    "                |                \n"  # row 1
    "                .                \n"  # row 2:  cemetery_gates
    "                |                \n"  # row 3
    "                .                \n"  # row 4:  north_road
    "                |                \n"  # row 5
    "    .   .   .---.---.   .   .   .\n"  # row 6:  shops N (inn at center)
    "    |   |   |   |   |   |   |   |\n"  # row 7
    ">---.---.---.---.---.---.---.---<\n"  # row 8:  main road
    "    |   |   |   |   |   |   |   |\n"  # row 9
    "    .   .   .---.---.   .   .   .\n"  # row 10: shops S (gen store at center)
    "                |                \n"  # row 11
    "                .                \n"  # row 12: south_road
    "                |                \n"  # row 13
    "            .---.---.            \n"  # row 14: beggars/mid_south/warriors
    "                |                \n"  # row 15
    "            .---.---.            \n"  # row 16: broken_crown/far_south/gaol
    "                |                \n"  # row 17
    "                .                "   # row 18: south_gate
)

# Map each point_key to grid position(s) and POI type.
# POI symbols are resolved at render time from poi_symbols.py.
_POINT_CELLS = {
    # ── Cemetery / North ──
    "cemetery":        {"pos": [(0,  16)], "poi": "cemetery"},
    "cemetery_gates":  {"pos": [(2,  16)], "poi": "road"},
    "north_road":      {"pos": [(4,  16)], "poi": "road"},
    # ── North-side shops (row 6, west to east) ──
    "textiles":        {"pos": [(6,   4)], "poi": "tailor"},
    "smithy":          {"pos": [(6,   8)], "poi": "smithy"},
    "woodshop":        {"pos": [(6,  12)], "poi": "woodshop"},
    "inn":             {"pos": [(6,  16)], "poi": "inn"},
    "stables":         {"pos": [(6,  20)], "poi": "stable"},
    "bakery":          {"pos": [(6,  24)], "poi": "bakery"},
    "apothecary":      {"pos": [(6,  28)], "poi": "apothecary"},
    "jeweller":        {"pos": [(6,  32)], "poi": "jeweller"},
    # ── The Old Trade Way (row 8) ──
    "road_far_west":   {"pos": [(8,   0)], "poi": "zone_exit"},
    "road_west":       {"pos": [(8,   4)], "poi": "road"},
    "road_mid_west":   {"pos": [(8,   8)], "poi": "road"},
    "sq_w":            {"pos": [(8,  12)], "poi": "road"},
    "sq_center":       {"pos": [(8,  16)], "poi": "market"},
    "sq_e":            {"pos": [(8,  20)], "poi": "road"},
    "road_east":       {"pos": [(8,  24)], "poi": "road"},
    "road_mid_east":   {"pos": [(8,  28)], "poi": "road"},
    "road_far_east":   {"pos": [(8,  32)], "poi": "zone_exit"},
    # ── South-side shops (row 10, west to east) ──
    "elena_house":     {"pos": [(10,  4)], "poi": "house"},
    "abandoned_house": {"pos": [(10,  8)], "poi": "house"},
    "gareth_house":    {"pos": [(10, 12)], "poi": "house"},
    "general_store":   {"pos": [(10, 16)], "poi": "shop"},
    "shrine":          {"pos": [(10, 20)], "poi": "temple"},
    "bank":            {"pos": [(10, 24)], "poi": "bank"},
    "mages_guild":     {"pos": [(10, 28)], "poi": "guild"},
    "leathershop":     {"pos": [(10, 32)], "poi": "leathershop"},
    # ── South road ──
    "south_road":      {"pos": [(12, 16)], "poi": "road"},
    "beggars_alley":   {"pos": [(14, 12)], "poi": "road"},
    "mid_south_road":  {"pos": [(14, 16)], "poi": "road"},
    "warriors_guild":  {"pos": [(14, 20)], "poi": "guild"},
    "broken_crown":    {"pos": [(16, 12)], "poi": "tavern"},
    "far_south_road":  {"pos": [(16, 16)], "poi": "road"},
    "gaol":            {"pos": [(16, 20)], "poi": "road"},
    "south_gate":      {"pos": [(18, 16)], "poi": "gate"},
}

register_map({
    "key":          "millholm_town",
    "display_name": "Millholm Town",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

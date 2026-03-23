"""
Millholm Town district map.

NOT included: building interiors, private spaces, the secret passage,
NPC back rooms. gareth_house omitted (shares space with general_store).

Point key → room tag convention:
    room.tags.add("millholm_town:<point_key>", category="map_cell")
"""

from world.cartography.map_registry import register_map

# Matching the target layout exactly. Cells at even columns, dashes connect.
# The 3x3 market square occupies cols 8,10,12 on rows 4,5,6.
# Shops flank the square on both sides.
#
#              0000000000111111111122
#              0123456789012345678901
# row 0:               C
# row 1:               @
# row 2:               #
# row 3:             I # H
# row 4:       T S W # # # B A J
# row 5:     X-#-#-#-#-#-#-#-#-#-X
# row 6:       h h * # # # $ P L
# row 7:             + # G
# row 8:             # # G
# row 9:             I # g
# row 10:              @

_TEMPLATE = (
    "          .          \n"  # row 0
    "          .          \n"  # row 1
    "          .          \n"  # row 2
    "        . . .        \n"  # row 3
    "  . . . . . . . . .  \n"  # row 4
    ".-.-.-.-.-.-.-.-.-.-.\n"  # row 5
    "  . . . . . . . . .  \n"  # row 6
    "        . . .        \n"  # row 7
    "        . . .        \n"  # row 8
    "        . . .        \n"  # row 9
    "          .          "    # row 10
)

_POINT_CELLS = {
    # ── Cemetery / North ──
    "cemetery":        {"pos": [(0, 10)], "poi": "cemetery"},
    "cemetery_gates":  {"pos": [(1, 10)], "poi": "gate"},
    "north_road":      {"pos": [(2, 10)], "poi": "road"},
    # ── Row 3: above square ──
    "inn":             {"pos": [(3,  8)], "poi": "inn"},
    "sq_n":            {"pos": [(3, 10), (4, 10)], "poi": "road"},
    "stables":         {"pos": [(3, 12)], "poi": "stable"},
    # ── Row 4: north shops + square top ──
    "textiles":        {"pos": [(4,  2)], "poi": "tailor"},
    "smithy":          {"pos": [(4,  4)], "poi": "smithy"},
    "woodshop":        {"pos": [(4,  6)], "poi": "woodshop"},
    "sq_nw":           {"pos": [(4,  8)], "poi": "road"},
    "sq_ne":           {"pos": [(4, 12)], "poi": "road"},
    "bakery":          {"pos": [(4, 14)], "poi": "bakery"},
    "apothecary":      {"pos": [(4, 16)], "poi": "apothecary"},
    "jeweller":        {"pos": [(4, 18)], "poi": "jeweller"},
    # ── Row 5: The Old Trade Way ──
    "road_far_west":   {"pos": [(5,  0)], "poi": "zone_exit"},
    "road_west":       {"pos": [(5,  2)], "poi": "road"},
    "road_mid_west":   {"pos": [(5,  4)], "poi": "road"},
    "sq_w":            {"pos": [(5,  6)], "poi": "road"},
    "sq_center":       {"pos": [(5,  8), (5, 10), (5, 12)], "poi": "road"},
    "sq_e":            {"pos": [(5, 14)], "poi": "road"},
    "road_east":       {"pos": [(5, 16)], "poi": "road"},
    "road_mid_east":   {"pos": [(5, 18)], "poi": "road"},
    "road_far_east":   {"pos": [(5, 20)], "poi": "zone_exit"},
    # ── Row 6: south shops + square bottom ──
    "elena_house":     {"pos": [(6,  2)], "poi": "house"},
    "abandoned_house": {"pos": [(6,  4)], "poi": "house"},
    "general_store":   {"pos": [(6,  6)], "poi": "shop"},
    "sq_sw":           {"pos": [(6,  8)], "poi": "road"},
    "sq_s":            {"pos": [(6, 10)], "poi": "road"},
    "sq_se":           {"pos": [(6, 12)], "poi": "road"},
    "bank":            {"pos": [(6, 14)], "poi": "bank"},
    "post_office":     {"pos": [(6, 16)], "poi": "post_office"},
    "leathershop":     {"pos": [(6, 18)], "poi": "leathershop"},
    # ── South road ──
    "shrine":          {"pos": [(7,  8)], "poi": "temple"},
    "south_road":      {"pos": [(7, 10)], "poi": "road"},
    "warriors_guild":  {"pos": [(7, 12)], "poi": "guild"},
    "beggars_alley":   {"pos": [(8,  8)], "poi": "road"},
    "mid_south_road":  {"pos": [(8, 10)], "poi": "road"},
    "mages_guild":     {"pos": [(8, 12)], "poi": "guild"},
    "broken_crown":    {"pos": [(9,  8)], "poi": "inn"},
    "far_south_road":  {"pos": [(9, 10)], "poi": "road"},
    "gaol":            {"pos": [(9, 12)], "poi": "gaol"},
    "south_gate":      {"pos": [(10, 10)], "poi": "gate"},
}

register_map({
    "key":          "millholm_town",
    "display_name": "Millholm Town",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

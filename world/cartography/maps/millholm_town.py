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
#            0000000000111111111122
#            0123456789012345678901
# row 0:               X  
# row 1:           C-g-#
# row 2:               #
# row 3:             I # H
# row 4:       S S S # # # B S S 
# row 5:     X-#-#-#-#-#-#-#-#-#-X
# row 6:       h h S # # # $ P v
# row 7:             + # G
# row 8:             # # G
# row 9          h W v # W W h
# row 10:        # # # # # # #
# row 11:        W v W # g v W
# row 12:            I # g
# row 13:              @


_TEMPLATE = (
    "          .          \n"  # row 0: lake track (north)
    "        .-.          \n"  # row 1: cemetery gate - north road
    "          .          \n"  # row 2
    "        .-.-.        \n"  # row 3
    "  .-.-.-.-.-.-.-.-.  \n"  # row 4
    ".-.-.-.-.-.-.-.-.-.-.\n"  # row 5
    "  .-.-.-.-.-.-.-.-.  \n"  # row 6
    "        .-.-.        \n"  # row 7
    "        .-.-.        \n"  # row 8
    "    .-.-.-.-.-.-.    \n"  # row 9
    "    .-.-.-.-.-.-.    \n"  # row 10
    "    .-.-.-.-.-.-.    \n"  # row 11
    "        .-.-.        \n"  # row 12
    "          .          "    # row 13
)

_POINT_CELLS = {
    # ── Row 0: north exit ──
    "lake_track":          {"pos": [(0, 10)], "poi": "zone_exit"},
    # ── Row 1: cemetery + north road ──
    "cemetery":            {"pos": [(1,  6)], "poi": "cemetery"},
    "cemetery_gates":      {"pos": [(1,  8)], "poi": "gate"},
    "north_road":          {"pos": [(1, 10), (2, 10)], "poi": "road"},
    # ── Row 3: above square ──
    "inn":                 {"pos": [(3,  8)], "poi": "inn"},
    "sq_n":                {"pos": [(3, 10), (4, 10)], "poi": "road"},
    "stables":             {"pos": [(3, 12)], "poi": "stable"},
    # ── Row 4: north shops + square top ──
    "weapons_shop":        {"pos": [(4,  2)], "poi": "shop"},
    "armorer":             {"pos": [(4,  4)], "poi": "shop"},
    "clothing_shop":       {"pos": [(4,  6)], "poi": "shop"},
    "sq_nw":               {"pos": [(4,  8)], "poi": "road"},
    "sq_ne":               {"pos": [(4, 12)], "poi": "road"},
    "bakery":              {"pos": [(4, 14)], "poi": "bakery"},
    "magical_supplies":    {"pos": [(4, 16)], "poi": "shop"},
    "jewellers_showroom":  {"pos": [(4, 18)], "poi": "shop"},
    # ── Row 5: The Old Trade Way ──
    "road_far_west":       {"pos": [(5,  0)], "poi": "zone_exit"},
    "road_west":           {"pos": [(5,  2)], "poi": "road"},
    "road_mid_west":       {"pos": [(5,  4)], "poi": "road"},
    "sq_w":                {"pos": [(5,  6)], "poi": "road"},
    "sq_center":           {"pos": [(5,  8), (5, 10), (5, 12)], "poi": "road"},
    "sq_e":                {"pos": [(5, 14)], "poi": "road"},
    "road_east":           {"pos": [(5, 16)], "poi": "road"},
    "road_mid_east":       {"pos": [(5, 18)], "poi": "road"},
    "road_far_east":       {"pos": [(5, 20)], "poi": "zone_exit"},
    # ── Row 6: south side of Trade Way ──
    "gareth_house":        {"pos": [(6,  2)], "poi": "house"},
    "abandoned_house":     {"pos": [(6,  4)], "poi": "house"},
    "general_store":       {"pos": [(6,  6)], "poi": "shop"},
    "sq_sw":               {"pos": [(6,  8)], "poi": "road"},
    "sq_s":                {"pos": [(6, 10)], "poi": "road"},
    "sq_se":               {"pos": [(6, 12)], "poi": "road"},
    "bank":                {"pos": [(6, 14)], "poi": "bank"},
    "post_office":         {"pos": [(6, 16)], "poi": "post_office"},
    "vacant_shop":         {"pos": [(6, 18)], "poi": "shop"},
    # ── Rows 7-8: south road (upper) ──
    "shrine":              {"pos": [(7,  8)], "poi": "temple"},
    "south_road":          {"pos": [(7, 10)], "poi": "road"},
    "mages_guild":         {"pos": [(7, 12)], "poi": "guild"},
    "beggars_alley":       {"pos": [(8,  8)], "poi": "road"},
    "mid_south_road":      {"pos": [(8, 10)], "poi": "road"},
    "warriors_guild":      {"pos": [(8, 12)], "poi": "guild"},
    # ── Row 9: north side of Artisan's Way ──
    "hendricks_house":     {"pos": [(9,  4)], "poi": "house"},
    "smithy":              {"pos": [(9,  6)], "poi": "workshop"},
    "vacant_w1":           {"pos": [(9,  8)], "poi": "shop"},
    "upper_south_road":    {"pos": [(9, 10)], "poi": "road"},
    "apothecary":          {"pos": [(9, 12)], "poi": "workshop"},
    "textiles":            {"pos": [(9, 14)], "poi": "workshop"},
    "elena_house":         {"pos": [(9, 16)], "poi": "house"},
    # ── Row 10: Artisan's Way lane ──
    "artisans_way_w3":     {"pos": [(10,  4)], "poi": "road"},
    "artisans_way_w2":     {"pos": [(10,  6)], "poi": "road"},
    "artisans_way_w1":     {"pos": [(10,  8)], "poi": "road"},
    "artisans_way":        {"pos": [(10, 10)], "poi": "road"},
    "artisans_way_e1":     {"pos": [(10, 12)], "poi": "road"},
    "artisans_way_e2":     {"pos": [(10, 14)], "poi": "road"},
    "artisans_way_e3":     {"pos": [(10, 16)], "poi": "road"},
    # ── Row 11: south side of Artisan's Way ──
    "leathershop":         {"pos": [(11,  4)], "poi": "workshop"},
    "vacant_w2":           {"pos": [(11,  6)], "poi": "shop"},
    "jeweller":            {"pos": [(11,  8)], "poi": "workshop"},
    "lower_south_road":    {"pos": [(11, 10)], "poi": "road"},
    "gaol":                {"pos": [(11, 12)], "poi": "gaol"},
    "vacant_e2":           {"pos": [(11, 14)], "poi": "shop"},
    "woodshop":            {"pos": [(11, 16)], "poi": "workshop"},
    # ── Row 12-13: far south road ──
    "broken_crown":        {"pos": [(12,  8)], "poi": "inn"},
    "far_south_road":      {"pos": [(12, 10)], "poi": "road"},
    "gaol_cell":           {"pos": [(12, 12)], "poi": "gaol"},
    "south_gate":          {"pos": [(13, 10)], "poi": "gate"},
}

register_map({
    "key":          "millholm_town",
    "display_name": "Millholm Town",
    "scale":        "district",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

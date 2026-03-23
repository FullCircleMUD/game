"""
Millholm Town district map.

Template: streets, road segments, building exteriors, landmarks.
NOT included: building interiors, private spaces, the secret passage.

Point key → room tag convention:
    room.tags.add("millholm_town:<point_key>", category="map_cell")

Template layout (33 cols × 19 rows):

    Row  0:   "                C                "  cemetery
    Row  2:   "                K                "  cemetery_gates
    Row  4:   "                N                "  north_road
    Row  6:   "            a---n---f            "  sq_nw / sq_n / sq_ne
    Row  8:   "W---w---m---A---X---B---p---e---E"  trade way + market square
    Row 10:   "            c---s---d            "  sq_sw / sq_s / sq_se
    Row 12:   "                1                "  south_road
    Row 14:   "                2                "  mid_south_road
    Row 16:   "                3                "  far_south_road
    Row 18:   "                G                "  south_gate
"""

from world.cartography.map_registry import register_map

_TEMPLATE = (
    "                C                \n"
    "                |                \n"
    "                K                \n"
    "                |                \n"
    "                N                \n"
    "                |                \n"
    "            a---n---f            \n"
    "            |   |   |            \n"
    "W---w---m---A---X---B---p---e---E\n"
    "            |   |   |            \n"
    "            c---s---d            \n"
    "                |                \n"
    "                1                \n"
    "                |                \n"
    "                2                \n"
    "                |                \n"
    "                3                \n"
    "                |                \n"
    "                G                "
)

# Map each point_key to grid position(s) and POI type.
# POI symbols are resolved at render time from poi_symbols.py.
_POINT_CELLS = {
    "cemetery":       {"pos": [(0,  16)], "poi": "cemetery"},
    "cemetery_gates": {"pos": [(2,  16)], "poi": "gate"},
    "north_road":     {"pos": [(4,  16)], "poi": "road"},
    "sq_nw":          {"pos": [(6,  12)], "poi": "square"},
    "sq_n":           {"pos": [(6,  16)], "poi": "square"},
    "sq_ne":          {"pos": [(6,  20)], "poi": "square"},
    "sq_w":           {"pos": [(8,  12)], "poi": "square"},
    "sq_center":      {"pos": [(8,  16)], "poi": "market"},
    "sq_e":           {"pos": [(8,  20)], "poi": "square"},
    "sq_sw":          {"pos": [(10, 12)], "poi": "square"},
    "sq_s":           {"pos": [(10, 16)], "poi": "square"},
    "sq_se":          {"pos": [(10, 20)], "poi": "square"},
    "south_road":     {"pos": [(12, 16)], "poi": "road"},
    "mid_south_road": {"pos": [(14, 16)], "poi": "road"},
    "far_south_road": {"pos": [(16, 16)], "poi": "road"},
    "south_gate":     {"pos": [(18, 16)], "poi": "gate"},
    "road_far_west":  {"pos": [(8,  0)],  "poi": "zone_exit"},
    "road_west":      {"pos": [(8,  4)],  "poi": "road"},
    "road_mid_west":  {"pos": [(8,  8)],  "poi": "road"},
    "road_mid_east":  {"pos": [(8,  24)], "poi": "road"},
    "road_east":      {"pos": [(8,  28)], "poi": "road"},
    "road_far_east":  {"pos": [(8,  32)], "poi": "zone_exit"},
}

register_map({
    "key":          "millholm_town",
    "display_name": "Millholm Town",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

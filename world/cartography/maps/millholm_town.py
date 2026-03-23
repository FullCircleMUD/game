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

# Map each point_key to a list of (row, col) positions in the template.
# All single-character room cells — one cell per room.
_POINT_CELLS = {
    "cemetery":       [(0,  16)],
    "cemetery_gates": [(2,  16)],
    "north_road":     [(4,  16)],
    "sq_nw":          [(6,  12)],
    "sq_n":           [(6,  16)],
    "sq_ne":          [(6,  20)],
    "sq_w":           [(8,  12)],
    "sq_center":      [(8,  16)],
    "sq_e":           [(8,  20)],
    "sq_sw":          [(10, 12)],
    "sq_s":           [(10, 16)],
    "sq_se":          [(10, 20)],
    "south_road":     [(12, 16)],
    "mid_south_road": [(14, 16)],
    "far_south_road": [(16, 16)],
    "south_gate":     [(18, 16)],
    "road_far_west":  [(8,  0)],
    "road_west":      [(8,  4)],
    "road_mid_west":  [(8,  8)],
    "road_mid_east":  [(8,  24)],
    "road_east":      [(8,  28)],
    "road_far_east":  [(8,  32)],
}

register_map({
    "key":          "millholm_town",
    "display_name": "Millholm Town",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

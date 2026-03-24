"""
Millholm Region overview map — stub.

Low-resolution overview of the entire Millholm zone. One cell per district
junction. Procedural deep woods is shown as a single vague marker surrounded
by unexplored cells — players see that something is out there but not how to
reach it.

Point key → room tag convention:
    room.tags.add("millholm_region:<point_key>", category="map_cell")

Notable: faerie hollow clearing and miners camp BOTH tag to "deep_woods" —
the same single cell. Surveying either room adds the same vague marker.
"""

from world.cartography.map_registry import register_map

# Minimal stub template — real art to be designed once region is fully built.
# 33 cols × 9 rows placeholder.
_TEMPLATE = (
    "           [MILLHOLM REGION]   \n"
    "  farm  .  town .  woods  .  .  \n"
    "    .   .   .   .   .   .   .   \n"
    "  south .  .   .   .   .   .   \n"
    "    .   .  .   .   .  ?   .   \n"
    "    .   .   .   .   .   .   .   \n"
    "    .  sewer  .  .   mine  .   \n"
    "    .   .   .   .   .   .   .   \n"
    "    .   .   .   .   .   .   .   "
)

_POINT_CELLS = {
    "millholm_town":     {"pos": [(1, 11)], "poi": "town"},
    "millholm_farms":    {"pos": [(1, 2)],  "poi": "farm"},
    "millholm_woods":    {"pos": [(1, 20)], "poi": "woods"},
    "millholm_southern": {"pos": [(3, 2)],  "poi": "district"},
    "deep_woods":        {"pos": [(4, 19)], "poi": "unknown"},  # shared: faerie hollow + mine entrance
    "millholm_sewers":   {"pos": [(6, 4)],  "poi": "tunnel"},
    "millholm_mine":     {"pos": [(6, 20)], "poi": "mine"},
}

register_map({
    "key":          "millholm_region",
    "display_name": "Millholm Region",
    "scale":        "region",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

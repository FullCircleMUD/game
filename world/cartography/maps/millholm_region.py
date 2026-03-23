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
    "           [MILLHAVEN REGION]   \n"
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
    "millholm_town":    [(1, 11)],
    "millholm_farms":   [(1, 2)],
    "millholm_woods":   [(1, 20)],
    "millholm_southern": [(3, 2)],
    "deep_woods":        [(4, 19)],  # shared: faerie hollow + mine entrance
    "millholm_sewers":  [(6, 4)],
    "millholm_mine":    [(6, 20)],
}

register_map({
    "key":          "millholm_region",
    "display_name": "Millholm Region",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

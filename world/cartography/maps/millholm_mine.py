"""
Millholm Mine district map — stub.

All mine rooms. The miners camp / mine entrance tags to BOTH millholm_mine
and millholm_region. Surveying that room updates both maps simultaneously
if both are held.

Point key → room tag convention:
    room.tags.add("millholm_mine:<point_key>", category="map_cell")
"""

from world.cartography.map_registry import register_map

# Stub template — real art to be designed with mine layout.
_TEMPLATE = (
    "      [MILLHOLM MINE]        \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  "
)

_POINT_CELLS = {
    "mine_entrance":     {"pos": [(1, 2)],   "poi": "gate"},      # also tagged millholm_region:deep_woods
    "entry_shaft":       {"pos": [(2, 2)],   "poi": "shaft"},
    "copper_drift":      {"pos": [(2, 6)],   "poi": "mine"},
    "copper_seam":       {"pos": [(2, 10)],  "poi": "mine"},
    "timbered_corridor": {"pos": [(3, 6)],   "poi": "tunnel"},
    "ore_cart_track":    {"pos": [(3, 10)],  "poi": "tunnel"},
    "kobold_lookout":    {"pos": [(4, 6)],   "poi": "lair"},
    "flooded_gallery":   {"pos": [(4, 10)],  "poi": "dead_end"},
    "descent_shaft":     {"pos": [(4, 2)],   "poi": "shaft"},
    "lower_junction":    {"pos": [(5, 2)],   "poi": "crossroads"},
    "tin_seam":          {"pos": [(5, 6)],   "poi": "mine"},
    "tin_vein":          {"pos": [(5, 10)],  "poi": "mine"},
    "kobold_warren":     {"pos": [(5, 14)],  "poi": "lair"},
    "ancient_passage":   {"pos": [(6, 2)],   "poi": "tunnel"},
    "sealed_door":       {"pos": [(6, 6)],   "poi": "dead_end"},
}

register_map({
    "key":          "millholm_mine",
    "display_name": "Millholm Mine",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

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
    "mine_entrance":     [(1, 2)],   # also tagged millholm_region:deep_woods
    "entry_shaft":       [(2, 2)],
    "copper_drift":      [(2, 6)],
    "copper_seam":       [(2, 10)],
    "timbered_corridor": [(3, 6)],
    "ore_cart_track":    [(3, 10)],
    "kobold_lookout":    [(4, 6)],
    "flooded_gallery":   [(4, 10)],
    "descent_shaft":     [(4, 2)],
    "lower_junction":    [(5, 2)],
    "tin_seam":          [(5, 6)],
    "tin_vein":          [(5, 10)],
    "kobold_warren":     [(5, 14)],
    "ancient_passage":   [(6, 2)],
    "sealed_door":       [(6, 6)],
}

register_map({
    "key":          "millholm_mine",
    "display_name": "Millholm Mine",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

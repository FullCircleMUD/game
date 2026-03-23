"""
Millholm Sewers district map — stub.

All sewer rooms. The crumbling wall room (thieves lair entrance) IS tagged —
the map shows something is there. The thieves lair interior is NOT tagged.

Point key → room tag convention:
    room.tags.add("millholm_sewers:<point_key>", category="map_cell")
"""

from world.cartography.map_registry import register_map

# Stub template — real art to be designed with sewer layout.
_TEMPLATE = (
    "      [MILLHOLM SEWERS]      \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  \n"
    "  .   .   .   .   .   .   .  "
)

_POINT_CELLS = {
    "sewer_entrance":    [(1, 2)],
    "main_drain":        [(2, 2)],
    "drain_junction":    [(3, 2)],
    "flooded_tunnel":    [(3, 6)],
    "deep_sewer":        [(4, 2)],
    "overflow_chamber":  [(5, 2)],
    "crumbling_wall":    [(5, 6)],
    "blocked_grate":     [(2, 6)],
    "rat_nest":          [(3, 10)],
    "collapsed_section": [(4, 6)],
    "old_cistern":       [(1, 10)],
    "waterlogged_passage": [(2, 10)],
    "fungal_grotto":     [(3, 14)],
    "narrow_crawlway":   [(4, 14)],
    "ancient_drain":     [(5, 14)],
    "submerged_alcove":  [(4, 18)],
    "bricked_passage":   [(5, 18)],
}

register_map({
    "key":          "millholm_sewers",
    "display_name": "Millholm Sewers",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

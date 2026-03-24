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
    "sewer_entrance":      {"pos": [(1, 2)],   "poi": "gate"},
    "main_drain":          {"pos": [(2, 2)],   "poi": "tunnel"},
    "drain_junction":      {"pos": [(3, 2)],   "poi": "crossroads"},
    "flooded_tunnel":      {"pos": [(3, 6)],   "poi": "tunnel"},
    "deep_sewer":          {"pos": [(4, 2)],   "poi": "tunnel"},
    "overflow_chamber":    {"pos": [(5, 2)],   "poi": "chamber"},
    "crumbling_wall":      {"pos": [(5, 6)],   "poi": "dead_end"},
    "blocked_grate":       {"pos": [(2, 6)],   "poi": "dead_end"},
    "rat_nest":            {"pos": [(3, 10)],  "poi": "lair"},
    "collapsed_section":   {"pos": [(4, 6)],   "poi": "dead_end"},
    "old_cistern":         {"pos": [(1, 10)],  "poi": "chamber"},
    "waterlogged_passage": {"pos": [(2, 10)],  "poi": "tunnel"},
    "fungal_grotto":       {"pos": [(3, 14)],  "poi": "chamber"},
    "narrow_crawlway":     {"pos": [(4, 14)],  "poi": "tunnel"},
    "ancient_drain":       {"pos": [(5, 14)],  "poi": "tunnel"},
    "submerged_alcove":    {"pos": [(4, 18)],  "poi": "dead_end"},
    "bricked_passage":     {"pos": [(5, 18)],  "poi": "dead_end"},
}

register_map({
    "key":          "millholm_sewers",
    "display_name": "Millholm Sewers",
    "scale":        "district",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

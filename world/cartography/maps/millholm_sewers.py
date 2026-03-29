"""
Millholm Sewers district map.

Shows the sewer proper only. The crumbling wall (thieves' lair entrance)
IS shown — the thieves' lair interior is NOT mapped (hidden district).

Two branches: main spine (left) and cistern branch (right), merging
at the Overflow Chamber / Ancient Drain at the bottom.

Point key → room tag convention:
    room.tags.add("millholm_sewers:<point_key>", category="map_cell")
"""

from world.cartography.map_registry import register_map

# Even column spacing, dashes connect — same convention as town map.
# Cells at cols 0, 2, 4, 6, 8, 10, 12
#
#          0000000000111
#          0123456789012
# row 0:   @       @       sewer entrance, old cistern
# row 1:   #       #       main drain, waterlogged passage
# row 2:   #-#-x   O-x     drain junction, eastern pipe, blocked grate / fungal grotto, submerged
# row 3:   #-!     #       flooded tunnel, rat nest / narrow crawlway
# row 4:   #-x     #       deep sewer, collapsed / ancient drain
# row 5:   O---#-#-x       overflow, (link), ancient drain, bricked-up
# row 6:   !               crumbling wall (→ thieves)

_TEMPLATE = (
    "  .       .  \n"    # r0
    "  .       .  \n"    # r1
    "  .-.-.   .-.\n"    # r2
    "  .-.     .  \n"    # r3
    "  .-.     .  \n"    # r4
    "  .---.-.-.  \n"    # r5
    "  .          "      # r6
)

_POINT_CELLS = {
    # ── Main spine (left) ──
    "sewer_entrance":      {"pos": [(0, 2)],  "poi": "gate"},
    "main_drain":          {"pos": [(1, 2)],  "poi": "road"},
    "drain_junction":      {"pos": [(2, 2)],  "poi": "road"},
    "eastern_pipe":        {"pos": [(2, 4)],  "poi": "road"},
    "blocked_grate":       {"pos": [(2, 6)],  "poi": "dead_end"},
    "flooded_tunnel":      {"pos": [(3, 2)],  "poi": "road"},
    "rat_nest":            {"pos": [(3, 4)],  "poi": "lair"},
    "deep_sewer":          {"pos": [(4, 2)],  "poi": "road"},
    "collapsed_section":   {"pos": [(4, 4)],  "poi": "dead_end"},
    "overflow_chamber":    {"pos": [(5, 2)],  "poi": "chamber"},
    "crumbling_wall":      {"pos": [(6, 2)],  "poi": "lair"},
    # ── Cistern branch (right) ──
    "old_cistern":         {"pos": [(0, 10)], "poi": "gate"},
    "waterlogged_passage": {"pos": [(1, 10)], "poi": "road"},
    "fungal_grotto":       {"pos": [(2, 10)], "poi": "chamber"},
    "submerged_alcove":    {"pos": [(2, 12)], "poi": "dead_end"},
    "narrow_crawlway":     {"pos": [(3, 10)], "poi": "road"},
    "ancient_drain":       {"pos": [(4, 10)], "poi": "road"},
    "bricked_passage":     {"pos": [(5, 10)], "poi": "dead_end"},
}

register_map({
    "key":          "millholm_sewers",
    "display_name": "Millholm Sewers",
    "scale":        "district",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

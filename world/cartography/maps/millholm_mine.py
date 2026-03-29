"""
Millholm Mine district map.

Three levels: surface (miners camp), upper mine (copper), lower mine
(tin). Descent shafts connect levels vertically, shown as `v`.

The miners camp / mine entrance tags to BOTH millholm_mine and
millholm_region. Surveying that room updates both maps simultaneously.

Point key → room tag convention:
    room.tags.add("millholm_mine:<point_key>", category="map_cell")
"""

from world.cartography.map_registry import register_map

# Even column spacing (cells at 0, 2, 4, 6, 8, 10).
# Same convention as town and sewer maps.
#
#          0000000000
#          0123456789
# row 0:   F              windroot hollow
# row 1:   #-@             miners camp, mine entrance
# row 2:     @-#           (cont), entry shaft
# row 3:   m   #           copper drift, timbered corridor
# row 4:   m   #           copper seam, ore cart track
# row 5:       !-x         kobold lookout, flooded gallery
# row 6:       v           descent shaft
# row 7:   m-#-m           tin seam, lower junction, tin vein
# row 8:     !             kobold warren
# row 9:     #             ancient passage
# row 10:    x             sealed door

_TEMPLATE = (
    "  .        \n"    # r0
    "  .--.     \n"    # r1
    "    .-.    \n"    # r2
    "  .   .    \n"    # r3
    "  .   .    \n"    # r4
    "      .-. \n"     # r5
    "      .   \n"     # r6
    "  .-.-.   \n"     # r7
    "    .      \n"    # r8
    "    .      \n"    # r9
    "    .      "      # r10
)

_POINT_CELLS = {
    # ── Surface ──
    "windroot_hollow":   {"pos": [(0, 2)],  "poi": "farm"},
    "miners_camp":       {"pos": [(1, 2)],  "poi": "road"},
    "mine_entrance":     {"pos": [(1, 4)],  "poi": "gate"},
    # ── Upper Mine (Copper Level) ──
    "entry_shaft":       {"pos": [(2, 4)],  "poi": "shaft"},
    "copper_drift":      {"pos": [(3, 2)],  "poi": "mine"},
    "timbered_corridor": {"pos": [(3, 6)],  "poi": "road"},
    "copper_seam":       {"pos": [(4, 2)],  "poi": "mine"},
    "ore_cart_track":    {"pos": [(4, 6)],  "poi": "road"},
    # ── Kobold Territory ──
    "kobold_lookout":    {"pos": [(5, 6)],  "poi": "lair"},
    "flooded_gallery":   {"pos": [(5, 8)],  "poi": "dead_end"},
    "descent_shaft":     {"pos": [(6, 6)],  "poi": "shaft"},
    # ── Lower Mine (Tin Level) ──
    "tin_seam":          {"pos": [(7, 2)],  "poi": "mine"},
    "lower_junction":    {"pos": [(7, 4)],  "poi": "road"},
    "tin_vein":          {"pos": [(7, 6)],  "poi": "mine"},
    "kobold_warren":     {"pos": [(8, 4)],  "poi": "lair"},
    # ── Deep Mine ──
    "ancient_passage":   {"pos": [(9, 4)],  "poi": "road"},
    "sealed_door":       {"pos": [(10, 4)], "poi": "dead_end"},
}

register_map({
    "key":          "millholm_mine",
    "display_name": "Millholm Mine",
    "scale":        "district",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

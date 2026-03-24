"""
Millholm Region overview map — zone-level.

Each cell represents an area or district, not individual rooms. Multiple
game rooms are tagged to the same cell — surveying any one reveals it.
Region scale: no adjacent cell revelation on survey.

Road connections shown with -- dashes. Wilderness adjacency implied by
spacing only.

Point key → room tag convention:
    room.tags.add("millholm_region:<point_key>", category="map_cell")
"""

from world.cartography.map_registry import register_map

# Region map: 3-char cell spacing (symbol at cols 0,3,6,9,12,15,18,21,24,27,30,33,36).
# Road dashes at cols between connected cells. Wilderness uses spaces.
#
# Target layout (from maps/drafts/millholm_region.md):
#
# col:  0  3  6  9  12 15 18 21 24 27 30 33 36
#
# r0:                                  F
# r1:                            ~  ~  M--D
# r2:                   C        ~  ?  ~
# r3:    F     F     T  T  T  R  ~  ~  ~
# r4: R--#--#--#--#--T--T--T--#--#--#--#--#--Z
# r5:       #        T  T  T  R  ~  ~  ~
# r6:       #--?        #        ~  R  ~
# r7:       #           #        ~  ~  ~
# r8:       #           F
# r9:       #           #
# r10:      #        ?--~--?
# r11:      #           #
# r12:      #--#--#--#--#
# r13:                  Z

#        0123456789012345678901234567890123456789
#        0         1         2         3
_TEMPLATE = (
    "                                 .         \n"  # r0:  windroot (c33)
    "                           .  .  .--.\n"        # r1:  deep_woods x2, mine, dungeon
    "                  .        .  .  .\n"           # r2:  cemetery, deep_woods x2, faerie
    "   .     .     .  .  .  .  .  .  .\n"          # r3:  farms, town top, sawmill, woods
    ".--.--.--.--.--.--.--.--.--.--.--.--.\n"         # r4:  main road
    "      .        .  .  .  .  .  .  .\n"          # r5:  south fork, town bot, smelter, woods
    "      .--.        .        .  .  .\n"          # r6:  south road, bandits, road, woods+tannery
    "      .           .        .  .  .\n"          # r7:  south road, road, woods
    "      .           .\n"                         # r8:  moonpetal, road
    "      .           .\n"                         # r9:  south road, road
    "      .        .--.--.\n"                       # r10: south road, ravaged--gnoll--barrow
    "      .           .\n"                         # r11: south road, road
    "      .--.--.--.--.          \n"               # r12: south approach road
    "                  .          "                  # r13: shadowsward gate
)

_POINT_CELLS = {
    # ── Deep Woods / Mine / Faerie (top) ──
    "windroot_hollow":    {"pos": [(0, 33)], "poi": "farm"},
    "deep_woods_nw":      {"pos": [(1, 27)], "poi": "woods"},
    "deep_woods_ne":      {"pos": [(1, 30)], "poi": "woods"},
    "mine_entrance":      {"pos": [(1, 33)], "poi": "region_mine"},
    "mine_dungeon":       {"pos": [(1, 36)], "poi": "region_dungeon"},
    "deep_woods_sw":      {"pos": [(2, 27)], "poi": "woods"},
    "faerie_hollow":      {"pos": [(2, 30)], "poi": "unknown"},
    "deep_woods_se":      {"pos": [(2, 33)], "poi": "woods"},
    # ── Cemetery ──
    "cemetery":           {"pos": [(2, 18)], "poi": "cemetery"},
    # ── Farms (north of road) ──
    "wheat_farm":         {"pos": [(3, 3)],  "poi": "farm"},
    "cotton_farm":        {"pos": [(3, 9)],  "poi": "farm"},
    # ── Town 3x3 ──
    "town_nw":            {"pos": [(3, 15)], "poi": "town"},
    "town_n":             {"pos": [(3, 18)], "poi": "town"},
    "town_ne":            {"pos": [(3, 21)], "poi": "town"},
    "town_w":             {"pos": [(4, 15)], "poi": "town"},
    "town_center":        {"pos": [(4, 18)], "poi": "town"},
    "town_e":             {"pos": [(4, 21)], "poi": "town"},
    "town_sw":            {"pos": [(5, 15)], "poi": "town"},
    "town_s":             {"pos": [(5, 18)], "poi": "town"},
    "town_se":            {"pos": [(5, 21)], "poi": "town"},
    # ── Sawmill / Smelter ──
    "sawmill":            {"pos": [(3, 24)], "poi": "resource_processing"},
    "smelter":            {"pos": [(5, 24)], "poi": "resource_processing"},
    # ── Woods (main path + southern grid) ──
    "woods_path_w":       {"pos": [(3, 27)], "poi": "woods"},
    "woods_path_mid":     {"pos": [(3, 30)], "poi": "woods"},
    "woods_path_e":       {"pos": [(3, 33)], "poi": "woods"},
    "woods_road_w":       {"pos": [(4, 24)], "poi": "road"},
    "woods_road_mid":     {"pos": [(4, 27)], "poi": "road"},
    "woods_road_e":       {"pos": [(4, 30)], "poi": "road"},
    "woods_road_far_e":   {"pos": [(4, 33)], "poi": "road"},
    "woods_south_w":      {"pos": [(5, 27)], "poi": "woods"},
    "woods_south_mid":    {"pos": [(5, 30)], "poi": "woods"},
    "woods_south_e":      {"pos": [(5, 33)], "poi": "woods"},
    "woods_deep_sw":      {"pos": [(6, 27)], "poi": "woods"},
    "tannery":            {"pos": [(6, 30)], "poi": "resource_processing"},
    "woods_deep_se":      {"pos": [(6, 33)], "poi": "woods"},
    "woods_far_sw":       {"pos": [(7, 27)], "poi": "woods"},
    "woods_far_mid":      {"pos": [(7, 30)], "poi": "woods"},
    "woods_far_se":       {"pos": [(7, 33)], "poi": "woods"},
    # ── Main E-W road ──
    "windmill":           {"pos": [(4, 0)],  "poi": "resource_processing"},
    "farm_road_w":        {"pos": [(4, 3)],  "poi": "road"},
    "farm_road_mid":      {"pos": [(4, 6)],  "poi": "road"},
    "farm_road_e":        {"pos": [(4, 9)],  "poi": "road"},
    "farm_road_far_e":    {"pos": [(4, 12)], "poi": "road"},
    "woods_exit":         {"pos": [(4, 36)], "poi": "zone_boundary"},
    # ── Southern district ──
    "south_fork":         {"pos": [(5, 6)],  "poi": "road"},
    "south_road_1":       {"pos": [(6, 6)],  "poi": "road"},
    "bandits":            {"pos": [(6, 9)],  "poi": "unknown"},
    "south_road_2":       {"pos": [(6, 18)], "poi": "road"},
    "south_road_3":       {"pos": [(7, 6)],  "poi": "road"},
    "south_road_4":       {"pos": [(7, 18)], "poi": "road"},
    "moonpetal_fields":   {"pos": [(8, 6)],  "poi": "farm"},
    "moonpetal_road":     {"pos": [(8, 18)], "poi": "farm"},
    "south_road_5":       {"pos": [(9, 6)],  "poi": "road"},
    "south_road_6":       {"pos": [(9, 18)], "poi": "road"},
    "south_road_gnoll":   {"pos": [(10, 6)],  "poi": "road"},
    "ravaged_farmstead":  {"pos": [(10, 15)], "poi": "unknown"},
    "gnoll_territory":    {"pos": [(10, 18)], "poi": "woods"},
    "barrow_hill":        {"pos": [(10, 21)], "poi": "unknown"},
    "south_road_7":       {"pos": [(11, 6)], "poi": "road"},
    "south_road_8":       {"pos": [(11, 18)], "poi": "road"},
    "south_approach_w":   {"pos": [(12, 6)], "poi": "road"},
    "south_approach_1":   {"pos": [(12, 9)], "poi": "road"},
    "south_approach_2":   {"pos": [(12, 12)], "poi": "road"},
    "south_approach_3":   {"pos": [(12, 15)], "poi": "road"},
    "south_approach_e":   {"pos": [(12, 18)], "poi": "road"},
    "shadowsward_gate":   {"pos": [(13, 18)], "poi": "zone_boundary"},
}

register_map({
    "key":          "millholm_region",
    "display_name": "Millholm Region",
    "scale":        "region",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

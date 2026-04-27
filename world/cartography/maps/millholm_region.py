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
# r0:                ~  L--Z ~         F
# r1:                ~  ~  ~     ~  ~  M--D--Z
# r2:                C--#        ~  ?  ~
# r3:    F     F     T  T  T  R  ~  ~  ~
# r4: R--#--#--#--#--T--T--T--#--#--#--#--#--Z
# r5:       #     R  T  T  T  R  ~  ~  ~
# r6:       #--?        @        ~  R  ~                            
# r7:       #--#--#--#--#        ~  ~  ~
# r8:              ? ~  #  ~ ?
# r9:                ~  #  ~ 
# r10:             ? ~  #  ~ ?
# r11:                  #
# r12:                  !--?
# r13:                  Z

#        0123456789012345678901234567890123456789
#        0         1         2         3
_TEMPLATE = (
    "               .  .--.  .        .         \n"  # r0:  scrub(c15), lake(c18)--far_shore(c21), scrub(c24), windroot(c33)
    "               .  .  .     .  .  .--.\n"        # r1:  scrub(c15,18,21), deep_woods x2, mine, dungeon
    "            .--.           .  .  .\n"           # r2:  cemetery(c12)--north_road(c15), deep_woods x2, faerie
    "   .     .     .  .  .  .  .  .  .\n"           # r3:  farms, town top, sawmill, woods
    ".--.--.--.--.--.--.--.--.--.--.--.--.\n"        # r4:  main road
    "      .     .  .  .  .  .  .  .  .\n"           # r5:  south_fork(c6), cotton_mill(c12), town_sw/s/se(c15/18/21), smelter(c24), woods_south x3
    "      .--.        .        .  .  .\n"           # r6:  farms_south_road_n(c6)--abandoned_farm(c9), south_gate(c18), woods_deep_sw/tannery/woods_deep_se(c27/30/33)
    "      .--.--.--.--.        .  .  .\n"           # r7:  farms_south_road_w/mw/me/e--forests_edge_cell(c6..c18), woods_far x3(c27/30/33)
    "            .  .  .  .  .\n"                    # r8:  moonpetal_2(c12), forest_nw(c15), forest_path_n(c18), forest_ne(c21), raven_sage(c24)
    "               .  .  .\n"                       # r9:  forest_mid_w(c15), forest_path_ravine(c18), forest_mid_e(c21)
    "            .  .  .  .  .\n"                    # r10: bobbin_camp(c12), forest_sw(c15), forest_path_s(c18), forest_se(c21), moonpetal_1(c24)
    "                  .\n"                          # r11: grasslands(c18)
    "                  .--.\n"                       # r12: gnoll_camp(c18)--barrow_underground(c21)
    "                  .          "                  # r13: shadowsward_gate(c18)
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
    # ── Lake (north of town, surrounded by scrubland) ──
    "lake_scrub_w":       {"pos": [(0, 15)], "poi": "woods"},
    "lake":               {"pos": [(0, 18)], "poi": "lake"},
    "lake_far_shore":     {"pos": [(0, 21)], "poi": "zone_boundary"},
    "lake_scrub_ne":      {"pos": [(0, 24)], "poi": "woods"},
    "lake_scrub_sw":      {"pos": [(1, 15)], "poi": "woods"},
    "lake_scrub_s":       {"pos": [(1, 18)], "poi": "woods"},
    "lake_scrub_se":      {"pos": [(1, 21)], "poi": "woods"},
    # ── Cemetery (west of town, connected to north road) ──
    "cemetery":           {"pos": [(2, 12)], "poi": "cemetery"},
    "north_road":         {"pos": [(2, 15)], "poi": "road"},
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
    # ── Farms south extension ─────────────────────────────────────
    "south_fork":              {"pos": [(5, 6)],  "poi": "road"},
    "cotton_mill":             {"pos": [(5, 12)], "poi": "resource_processing"},
    "farms_south_road_n":      {"pos": [(6, 6)],  "poi": "road"},
    "abandoned_farm":          {"pos": [(6, 9)],  "poi": "unknown"},
    "farms_south_road_w":      {"pos": [(7, 6)],  "poi": "road"},
    "farms_south_road_mw":     {"pos": [(7, 9)],  "poi": "road"},
    "farms_south_road_me":     {"pos": [(7, 12)], "poi": "road"},
    "farms_south_road_e":      {"pos": [(7, 15)], "poi": "road"},
    # ── Town south gate (region-scale tag) ────────────────────────
    "south_gate":              {"pos": [(6, 18)], "poi": "gate"},
    # ── Southern district ─────────────────────────────────────────
    "forests_edge_cell":       {"pos": [(7, 18)], "poi": "road"},
    "moonpetal_2":             {"pos": [(8, 12)], "poi": "unknown"},
    "forest_nw":               {"pos": [(8, 15)], "poi": "woods"},
    "forest_path_n":           {"pos": [(8, 18)], "poi": "road"},
    "forest_ne":               {"pos": [(8, 21)], "poi": "woods"},
    "raven_sage":              {"pos": [(8, 24)], "poi": "unknown"},
    "forest_mid_w":            {"pos": [(9, 15)], "poi": "woods"},
    "forest_path_ravine":      {"pos": [(9, 18)], "poi": "road"},
    "forest_mid_e":            {"pos": [(9, 21)], "poi": "woods"},
    "bobbin_camp":             {"pos": [(10, 12)], "poi": "unknown"},
    "forest_sw":               {"pos": [(10, 15)], "poi": "woods"},
    "forest_path_s":           {"pos": [(10, 18)], "poi": "road"},
    "forest_se":               {"pos": [(10, 21)], "poi": "woods"},
    "moonpetal_1":             {"pos": [(10, 24)], "poi": "unknown"},
    "grasslands":              {"pos": [(11, 18)], "poi": "road"},
    "gnoll_camp":              {"pos": [(12, 18)], "poi": "lair"},
    "barrow_underground":      {"pos": [(12, 21)], "poi": "unknown"},
    "shadowsward_gate":        {"pos": [(13, 18)], "poi": "zone_boundary"},
}

register_map({
    "key":          "millholm_region",
    "display_name": "Millholm Region",
    "scale":        "region",
    "template":     _TEMPLATE,
    "point_cells":  _POINT_CELLS,
})

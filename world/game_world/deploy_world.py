"""
Master world deploy — builds all active zones and wires cross-zone connections.

Usage (Evennia shell):
    from world.game_world.deploy_world import deploy_world, soft_deploy_world
    deploy_world()         # build all active zones (assumes world already clean)
    soft_deploy_world()    # wipe all active zones + rebuild from scratch

To redeploy a single zone without touching others, use that zone's own script:
    from world.game_world.zones.millholm.soft_deploy import soft_deploy
    soft_deploy()
"""

from evennia import create_object, search_object

from world.game_world.zone_utils import clean_zone

RECYCLE_BIN_KEY = "nft_recycle_bin"
PURGATORY_KEY = "Purgatory"

# Zones included in a full world deploy.
# Comment out zones that are not yet built — their stubs will be skipped.
ACTIVE_ZONES = [
    "millholm",
    # "ironback_peaks",    # BASIC cartography — not yet built
    # "cloverfen",         # BASIC cartography — not yet built
    # "teotlan_ruin",      # BASIC sea island — not yet built
    # "calenport",         # BASIC sea island — not yet built
    # "shadowsward",       # SKILLED cartography — not yet built
    # "saltspray_bay",     # SKILLED cartography — not yet built
    # "bayou",             # SKILLED cartography — not yet built
    # "kashoryu",          # SKILLED sea / EXPERT overland — not yet built
    # "port_shadowmere",   # SKILLED sea — not yet built
    # "amber_shore",       # SKILLED sea — not yet built
    # "shadowroot",            # EXPERT cartography — not yet built
    # "scalded_waste",     # EXPERT cartography — not yet built
    # "arcane_sanctum",    # EXPERT sea — not yet built
    # "oldbone_island",    # EXPERT sea — not yet built
    # "aethenveil",        # MASTER cartography — not yet built
    # "zharavan",       # MASTER cartography — not yet built
    # "guildmere_island",  # MASTER sea — not yet built
    # "atlantis",          # MASTER dive (from Guildmere Island) — not yet built
    # "vaathari",          # GRANDMASTER sea — not yet built
]


def _ensure_system_room(key, typeclass_path, desc=None):
    existing = search_object(key, exact=True)
    if existing:
        print(f"  {key} already exists: {existing[0].dbref}")
        return existing[0]
    room = create_object(typeclass_path, key=key)
    if desc:
        room.db.desc = desc
    room.tags.add("system_zone", category="zone")
    room.tags.add("system_district", category="district")
    print(f"  Created {key}: {room.dbref}")
    return room


def _ensure_system_rooms():
    _ensure_system_room(
        RECYCLE_BIN_KEY,
        "typeclasses.terrain.rooms.room_recycle_bin.RoomRecycleBin",
        "A hidden room where orphaned NFT items are despawned and recycled.",
    )
    _ensure_system_room(
        PURGATORY_KEY,
        "typeclasses.terrain.rooms.room_purgatory.RoomPurgatory",
    )


def deploy_world():
    """
    Build all active zones and wire cross-zone connections.

    Each zone's build_zone() returns a gateway_rooms dict. Cross-zone exits
    are created here using those gateway rooms. Uncomment zone imports and
    connection lines as zones are built.
    """
    print("=== DEPLOYING WORLD ===\n")

    _ensure_system_rooms()

    # ── Build active zones ───────────────────────────────────────────
    from world.game_world.zones.millholm.soft_deploy import build_zone as build_millholm
    millholm_gateways = build_millholm()

    # Uncomment as zones are built:
    #
    # from world.game_world.zones.ironback_peaks.soft_deploy import build_zone as build_ironback_peaks
    # ironback_gateways = build_ironback_peaks()
    #
    # from world.game_world.zones.cloverfen.soft_deploy import build_zone as build_cloverfen
    # cloverfen_gateways = build_cloverfen()
    #
    # from world.game_world.zones.shadowsward.soft_deploy import build_zone as build_shadowsward
    # shadowsward_gateways = build_shadowsward()
    #
    # from world.game_world.zones.saltspray_bay.soft_deploy import build_zone as build_saltspray_bay
    # saltspray_gateways = build_saltspray_bay()
    #
    # from world.game_world.zones.bayou.soft_deploy import build_zone as build_bayou
    # bayou_gateways = build_bayou()
    #
    # from world.game_world.zones.kashoryu.soft_deploy import build_zone as build_kashoryu
    # kashoryu_gateways = build_kashoryu()
    #
    # from world.game_world.zones.shadowroot.soft_deploy import build_zone as build_blight
    # blight_gateways = build_blight()
    #
    # from world.game_world.zones.scalded_waste.soft_deploy import build_zone as build_scalded_waste
    # scalded_waste_gateways = build_scalded_waste()
    #
    # from world.game_world.zones.aethenveil.soft_deploy import build_zone as build_aethenveil
    # aethenveil_gateways = build_aethenveil()
    #
    # from world.game_world.zones.zharavan.soft_deploy import build_zone as build_zharavan
    # zharavan_gateways = build_zharavan()
    #
    # from world.game_world.zones.guildmere_island.soft_deploy import build_zone as build_guildmere_island
    # guildmere_gateways = build_guildmere_island()
    #
    # from world.game_world.zones.atlantis.soft_deploy import build_zone as build_atlantis
    # atlantis_gateways = build_atlantis()
    #
    # from world.game_world.zones.vaathari.soft_deploy import build_zone as build_vaathari
    # vaathari_gateways = build_vaathari()

    # ── Cross-zone connections ───────────────────────────────────────
    # Wire gateway exits between zones as they are built. Each pair of lines
    # connects two zones bidirectionally via their gateway rooms.
    #
    # from utils.exit_helpers import connect
    #
    # Millholm → BASIC ring:
    # connect(millholm_gateways["north_road_end"], ironback_gateways["south_entrance"], "north")
    # connect(millholm_gateways["east_road_end"], cloverfen_gateways["west_entrance"], "east")
    #
    # Millholm → SKILLED ring (via shadowsward_gate):
    # connect(millholm_gateways["shadowsward_gate"], shadowsward_gateways["millholm_entrance"], "south")
    #
    # BASIC → SKILLED ring:
    # connect(ironback_gateways["saltspray_exit"], saltspray_gateways["ironback_entrance"], ...)
    # connect(ironback_gateways["shadowsward_exit"], shadowsward_gateways["ironback_entrance"], ...)
    # connect(cloverfen_gateways["bayou_exit"], bayou_gateways["cloverfen_entrance"], ...)
    #
    # SKILLED → EXPERT ring:
    # connect(bayou_gateways["kashoryu_exit"], kashoryu_gateways["bayou_entrance"], ...)
    # connect(bayou_gateways["blight_exit"], blight_gateways["bayou_entrance"], ...)
    # connect(saltspray_gateways["scalded_waste_exit"], scalded_waste_gateways["saltspray_entrance"], ...)
    #
    # EXPERT → MASTER ring:
    # connect(blight_gateways["aethenveil_exit"], aethenveil_gateways["blight_entrance"], ...)
    # connect(scalded_waste_gateways["zharavan_exit"], zharavan_gateways["scalded_entrance"], ...)
    # connect(aethenveil_gateways["kashoryu_exit"], kashoryu_gateways["aethenveil_entrance"], ...)
    #
    # MASTER → GRANDMASTER:
    # (sea route only — wired via RoomGateway + sail command, not direct exit)

    print("=== WORLD DEPLOY COMPLETE ===\n")


def soft_deploy_world():
    """Wipe all active zones and rebuild the full world from scratch."""
    print("=== SOFT DEPLOY WORLD ===\n")
    for zone_key in ACTIVE_ZONES:
        clean_zone(zone_key)
    deploy_world()

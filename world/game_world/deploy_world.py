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
    "ironback_peaks",    # BASIC cartography — scaffold
    "cloverfen",         # BASIC cartography — scaffold
    "shadowsward",       # SKILLED cartography — scaffold (temp endpoint)
    "saltspray_bay",     # SKILLED cartography — scaffold (temp endpoint)
    # "teotlan_ruin",      # BASIC sea island — not yet built
    # "calenport",         # BASIC sea island — not yet built
    # "bayou",             # SKILLED cartography — not yet built
    # "kashoryu",          # SKILLED sea / EXPERT overland — not yet built
    # "port_shadowmere",   # SKILLED sea — not yet built
    # "amber_shore",       # SKILLED sea — not yet built
    # "shadowroot",        # EXPERT cartography — not yet built
    # "scalded_waste",     # EXPERT cartography — not yet built
    # "arcane_sanctum",    # EXPERT sea — not yet built
    # "oldbone_island",    # EXPERT sea — not yet built
    # "aethenveil",        # MASTER cartography — not yet built
    # "zharavan",          # MASTER cartography — not yet built
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
    millholm = build_millholm()

    from world.game_world.zones.ironback_peaks.soft_deploy import build_zone as build_ironback
    ironback = build_ironback()

    from world.game_world.zones.cloverfen.soft_deploy import build_zone as build_cloverfen
    cloverfen = build_cloverfen()

    from world.game_world.zones.shadowsward.soft_deploy import build_zone as build_shadowsward
    shadowsward = build_shadowsward()

    from world.game_world.zones.saltspray_bay.soft_deploy import build_zone as build_saltspray
    saltspray = build_saltspray()

    # Uncomment as zones are built:
    # from world.game_world.zones.bayou.soft_deploy import build_zone as build_bayou
    # bayou = build_bayou()
    # from world.game_world.zones.kashoryu.soft_deploy import build_zone as build_kashoryu
    # kashoryu = build_kashoryu()
    # from world.game_world.zones.shadowroot.soft_deploy import build_zone as build_shadowroot
    # shadowroot = build_shadowroot()
    # from world.game_world.zones.scalded_waste.soft_deploy import build_zone as build_scalded_waste
    # scalded_waste = build_scalded_waste()
    # from world.game_world.zones.aethenveil.soft_deploy import build_zone as build_aethenveil
    # aethenveil = build_aethenveil()
    # from world.game_world.zones.zharavan.soft_deploy import build_zone as build_zharavan
    # zharavan = build_zharavan()
    # from world.game_world.zones.guildmere_island.soft_deploy import build_zone as build_guildmere
    # guildmere = build_guildmere()
    # from world.game_world.zones.atlantis.soft_deploy import build_zone as build_atlantis
    # atlantis = build_atlantis()
    # from world.game_world.zones.vaathari.soft_deploy import build_zone as build_vaathari
    # vaathari = build_vaathari()

    # ── Cross-zone gateway destinations ────────────────────────────────
    # Each RoomGateway gets a destinations list with travel conditions.
    # Routes are bidirectional — each side stores the reverse.

    print("[WIRING] Setting cross-zone gateway destinations...")

    # ── Millholm east gate (BASIC) ─────────────────────────────────────
    # Destinations: Ironback Peaks SW gate, Cloverfen NW gate
    millholm["east_gate"].destinations = [
        {
            "key": "ironback_peaks",
            "label": "Ironback Peaks",
            "destination": ironback["sw_gate"],
            "travel_description": (
                "You follow the trail northeast into the foothills. The "
                "air grows colder as the land rises, and soon the iron-grey "
                "peaks loom above you."
            ),
            "conditions": {"food_cost": 3},
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "cloverfen",
            "label": "Cloverfen",
            "destination": cloverfen["nw_gate"],
            "travel_description": (
                "You take the southern fork across gentle rolling plains. "
                "The grass grows greener and the hedgerows thicker as you "
                "enter halfling country."
            ),
            "conditions": {"food_cost": 2},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Ironback Peaks SW gate (BASIC) ─────────────────────────────────
    # Destinations: Millholm east gate, Cloverfen NW gate
    ironback["sw_gate"].destinations = [
        {
            "key": "millholm",
            "label": "Millholm",
            "destination": millholm["east_gate"],
            "travel_description": (
                "You descend from the mountain pass back through the "
                "wooded foothills. The familiar farmlands of Millholm "
                "spread before you."
            ),
            "conditions": {"food_cost": 3},
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "cloverfen",
            "label": "Cloverfen",
            "destination": cloverfen["nw_gate"],
            "travel_description": (
                "The trail descends from the mountains onto open lowland "
                "plains. The scent of wildflowers replaces the thin "
                "mountain air."
            ),
            "conditions": {"food_cost": 2},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Ironback Peaks S gate (SKILLED) ────────────────────────────────
    # Destination: Saltspray Bay W gate
    ironback["s_gate"].destinations = [
        {
            "key": "saltspray_bay",
            "label": "Saltspray Bay",
            "destination": saltspray["w_gate"],
            "travel_description": (
                "The mountain trail descends through alpine forest, "
                "switchbacking down until the salt air reaches you and "
                "the harbour spreads below."
            ),
            "conditions": {"food_cost": 4},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Cloverfen NW gate (BASIC) ──────────────────────────────────────
    # Destinations: Millholm east gate, Ironback Peaks SW gate
    cloverfen["nw_gate"].destinations = [
        {
            "key": "millholm",
            "label": "Millholm",
            "destination": millholm["east_gate"],
            "travel_description": (
                "You follow the road northwest across the plains. The "
                "land rises gently and familiar woods appear on the "
                "horizon — Millholm is close."
            ),
            "conditions": {"food_cost": 2},
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "ironback_peaks",
            "label": "Ironback Peaks",
            "destination": ironback["sw_gate"],
            "travel_description": (
                "You head north from the halfling plains into rising "
                "foothills. The air cools and the peaks grow larger "
                "with every step."
            ),
            "conditions": {"food_cost": 2},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Cloverfen E gate (SKILLED) ─────────────────────────────────────
    # Destination: Saltspray Bay W gate
    cloverfen["e_gate"].destinations = [
        {
            "key": "saltspray_bay",
            "label": "Saltspray Bay",
            "destination": saltspray["w_gate"],
            "travel_description": (
                "The trade road carries you east across open country. "
                "The air grows salty as the coast nears, and soon the "
                "masts of Saltspray Bay appear."
            ),
            "conditions": {"food_cost": 3},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Saltspray Bay W gate (SKILLED) ─────────────────────────────────
    # Destinations: Ironback Peaks S gate, Cloverfen E gate
    saltspray["w_gate"].destinations = [
        {
            "key": "ironback_peaks",
            "label": "Ironback Peaks",
            "destination": ironback["s_gate"],
            "travel_description": (
                "You leave the harbour behind and climb westward into "
                "the foothills. The peaks of the Ironback range grow "
                "steadily larger."
            ),
            "conditions": {"food_cost": 4},
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "cloverfen",
            "label": "Cloverfen",
            "destination": cloverfen["e_gate"],
            "travel_description": (
                "The road heads west across pastoral countryside, "
                "leaving the salt air behind. Neat hedgerows and "
                "round doors signal halfling lands ahead."
            ),
            "conditions": {"food_cost": 3},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Millholm south gate (SKILLED) ──────────────────────────────────
    # Destination: Shadowsward NE gate
    millholm["shadowsward_gate"].destinations = [
        {
            "key": "shadowsward",
            "label": "The Shadowsward",
            "destination": shadowsward["ne_gate"],
            "travel_description": (
                "You pass through the crumbling gatehouse and onto the "
                "open frontier. The land flattens into wind-scoured "
                "grassland, and distant watchtowers dot the horizon."
            ),
            "conditions": {"food_cost": 4},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Shadowsward NE gate (SKILLED) ──────────────────────────────────
    # Destination: Millholm south gate
    shadowsward["ne_gate"].destinations = [
        {
            "key": "millholm",
            "label": "Millholm",
            "destination": millholm["shadowsward_gate"],
            "travel_description": (
                "You follow the road northeast, leaving the frontier "
                "behind. The land grows greener and the familiar stone "
                "gatehouse of Millholm's southern boundary appears."
            ),
            "conditions": {"food_cost": 4},
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    print("  All cross-zone destinations wired.")

    # ── Future cross-zone connections (uncomment as zones are built) ──
    # Cloverfen → Bayou (SKILLED)
    # Saltspray Bay → Bayou (SKILLED)
    # Saltspray Bay dock → sea routes (SKILLED+)
    # Shadowsward → Shadowroot (EXPERT)
    # Shadowsward → Scalded Waste (EXPERT)
    # Bayou → Kashoryu (EXPERT)
    # Kashoryu dock → sea routes (SKILLED+)
    # Scalded Waste → Aethenveil (MASTER)
    # Scalded Waste → Zharavan (MASTER, hidden)
    # Aethenveil → Kashoryu (MASTER)
    # Guildmere Island → Atlantis (MASTER, dive)
    # Guildmere Island dock → Vaathari (GM)

    print("=== WORLD DEPLOY COMPLETE ===\n")


def soft_deploy_world():
    """Wipe all active zones and rebuild the full world from scratch."""
    print("=== SOFT DEPLOY WORLD ===\n")
    for zone_key in ACTIVE_ZONES:
        clean_zone(zone_key)
    deploy_world()

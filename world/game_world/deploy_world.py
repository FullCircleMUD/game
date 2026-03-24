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

from enums.mastery_level import MasteryLevel
from world.game_world.zone_utils import clean_zone

# Shorthand for route conditions
_BASIC = MasteryLevel.BASIC.value
_SKILLED = MasteryLevel.SKILLED.value
_EXPERT = MasteryLevel.EXPERT.value
_MASTER = MasteryLevel.MASTER.value
_GRANDMASTER = MasteryLevel.GRANDMASTER.value

RECYCLE_BIN_KEY = "nft_recycle_bin"
PURGATORY_KEY = "Purgatory"

# Zones included in a full world deploy.
# Comment out zones that are not yet built — their stubs will be skipped.
ACTIVE_ZONES = [
    "millholm",
    "ironback_peaks",    # BASIC cartography — scaffold
    "cloverfen",         # BASIC cartography — scaffold
    "shadowsward",       # SKILLED cartography — scaffold
    "saltspray_bay",     # SKILLED cartography — scaffold
    "bayou",             # SKILLED cartography — scaffold
    "kashoryu",          # SKILLED sea / EXPERT overland — scaffold
    "aethenveil",        # MASTER cartography — scaffold
    "teotlan_ruin",      # BASIC sea island — scaffold
    "calenport",         # SKILLED sea island — scaffold
    "port_shadowmere",   # SKILLED sea — scaffold
    "amber_shore",       # BASIC sea — scaffold
    "arcane_sanctum",    # EXPERT sea — scaffold
    "oldbone_island",    # EXPERT sea — scaffold
    "solendra",          # GRANDMASTER sea — scaffold
    "shadowroot",        # EXPERT cartography — scaffold
    "scalded_waste",     # MASTER cartography — scaffold
    "zharavan",          # GRANDMASTER cartography — scaffold
    "guildmere_island",  # MASTER sea — scaffold
    "atlantis",          # MASTER dive (from Guildmere Island) — scaffold
    "vaathari",          # GRANDMASTER sea — scaffold
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

    from world.game_world.zones.bayou.soft_deploy import build_zone as build_bayou
    bayou = build_bayou()

    from world.game_world.zones.kashoryu.soft_deploy import build_zone as build_kashoryu
    kashoryu = build_kashoryu()

    from world.game_world.zones.aethenveil.soft_deploy import build_zone as build_aethenveil
    aethenveil = build_aethenveil()

    from world.game_world.zones.teotlan_ruin.soft_deploy import build_zone as build_teotlan
    teotlan = build_teotlan()

    from world.game_world.zones.calenport.soft_deploy import build_zone as build_calenport
    calenport = build_calenport()

    from world.game_world.zones.port_shadowmere.soft_deploy import build_zone as build_shadowmere
    shadowmere = build_shadowmere()

    from world.game_world.zones.amber_shore.soft_deploy import build_zone as build_amber
    amber = build_amber()

    from world.game_world.zones.arcane_sanctum.soft_deploy import build_zone as build_sanctum
    sanctum = build_sanctum()

    from world.game_world.zones.oldbone_island.soft_deploy import build_zone as build_oldbone
    oldbone = build_oldbone()

    from world.game_world.zones.solendra.soft_deploy import build_zone as build_solendra
    solendra = build_solendra()

    from world.game_world.zones.shadowroot.soft_deploy import build_zone as build_shadowroot
    shadowroot = build_shadowroot()

    from world.game_world.zones.scalded_waste.soft_deploy import build_zone as build_scalded_waste
    scalded_waste = build_scalded_waste()

    from world.game_world.zones.zharavan.soft_deploy import build_zone as build_zharavan
    zharavan = build_zharavan()

    from world.game_world.zones.guildmere_island.soft_deploy import build_zone as build_guildmere
    guildmere = build_guildmere()

    from world.game_world.zones.atlantis.soft_deploy import build_zone as build_atlantis
    atlantis = build_atlantis()

    from world.game_world.zones.vaathari.soft_deploy import build_zone as build_vaathari
    vaathari = build_vaathari()
    # from world.game_world.zones.vaathari.soft_deploy import build_zone as build_vaathari
    # vaathari = build_vaathari()

    # ── Cross-zone gateway destinations ────────────────────────────────
    # Each RoomGateway gets a destinations list with travel conditions.
    # Routes are bidirectional — each side stores the reverse.

    print("[WIRING] Setting cross-zone gateway destinations...")

    # ── Millholm east gate (BASIC) ─────────────────────────────────────
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
            "required_cartography_tier": _BASIC,
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
            "required_cartography_tier": _BASIC,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Ironback Peaks SW gate (BASIC) ─────────────────────────────────
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
            "required_cartography_tier": _BASIC,
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
            "required_cartography_tier": _BASIC,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Ironback Peaks S gate (BASIC / SKILLED) ─────────────────────────
    ironback["s_gate"].destinations = [
        {
            "key": "cloverfen",
            "label": "Cloverfen",
            "destination": cloverfen["e_gate"],
            "travel_description": (
                "The trail descends from the southern peaks into open "
                "lowland. The air warms and tidy hedgerows appear as "
                "you enter the pastoral halfling country of Cloverfen."
            ),
            "conditions": {"food_cost": 2},
            "required_cartography_tier": _BASIC,
            "hidden": True,
            "explore_chance": 20,
        },
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
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Cloverfen NW gate (BASIC / SKILLED) ─────────────────────────────
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
            "required_cartography_tier": _BASIC,
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
            "required_cartography_tier": _BASIC,
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "shadowsward",
            "label": "The Shadowsward",
            "destination": shadowsward["ne_gate"],
            "travel_description": (
                "You strike out westward across open country. The "
                "hedgerows thin and the land flattens into wind-scoured "
                "grassland. Distant watchtowers mark the frontier ahead."
            ),
            "conditions": {"food_cost": 3},
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Cloverfen E gate (BASIC / SKILLED) ───────────────────────────────
    cloverfen["e_gate"].destinations = [
        {
            "key": "ironback_peaks",
            "label": "Ironback Peaks",
            "destination": ironback["s_gate"],
            "travel_description": (
                "The road climbs north from the halfling plains into "
                "rising foothills. The air cools and the iron-grey "
                "peaks grow steadily larger."
            ),
            "conditions": {"food_cost": 2},
            "required_cartography_tier": _BASIC,
            "hidden": True,
            "explore_chance": 20,
        },
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
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "bayou",
            "label": "The Bayou",
            "destination": bayou["n_gate"],
            "travel_description": (
                "The road south grows softer as hedgerows give way to "
                "reeds and willows. The air thickens with humidity and "
                "the drone of insects heralds the swamp ahead."
            ),
            "conditions": {"food_cost": 4},
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Saltspray Bay W gate (SKILLED) ─────────────────────────────────
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
            "required_cartography_tier": _SKILLED,
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
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "bayou",
            "label": "The Bayou",
            "destination": bayou["n_gate"],
            "travel_description": (
                "The coast road leads south past sandstone cliffs into "
                "warmer, more humid country. The vegetation thickens as "
                "the Bayou approaches."
            ),
            "conditions": {"food_cost": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Saltspray Bay dock (sea routes) ────────────────────────────────
    saltspray["dock"].destinations = [
        {
            "key": "teotlan_ruin",
            "label": "Teotlan Ruin",
            "destination": teotlan["dock"],
            "travel_description": "You sail south to the jungle ruins of Teotlan.",
            "conditions": {"food_cost": 3, "boat_level": 1},
            "required_cartography_tier": _BASIC,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "amber_shore",
            "label": "Amber Shore",
            "destination": amber["dock"],
            "travel_description": "You sail to the plague-touched colony of Amber Shore.",
            "conditions": {"food_cost": 3, "boat_level": 1},
            "required_cartography_tier": _BASIC,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "port_shadowmere",
            "label": "Port Shadowmere",
            "destination": shadowmere["dock"],
            "travel_description": "You sail into the perpetual twilight of Port Shadowmere.",
            "conditions": {"food_cost": 6, "boat_level": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "calenport",
            "label": "Calenport",
            "destination": calenport["dock"],
            "travel_description": "You sail to the pirate haven of Calenport.",
            "conditions": {"food_cost": 6, "boat_level": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "kashoryu",
            "label": "Kashoryu",
            "destination": kashoryu["dock"],
            "travel_description": "You sail the long coastal route to the tropical city of Kashoryu.",
            "conditions": {"food_cost": 6, "boat_level": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "arcane_sanctum",
            "label": "The Arcane Sanctum",
            "destination": sanctum["dock"],
            "travel_description": "You sail into open ocean toward the mist-shrouded Arcane Sanctum.",
            "conditions": {"food_cost": 8, "boat_level": 3},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "oldbone_island",
            "label": "Oldbone Island",
            "destination": oldbone["dock"],
            "travel_description": "You sail to the primordial shores of Oldbone Island.",
            "conditions": {"food_cost": 8, "boat_level": 3},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Bayou N gate (SKILLED) ─────────────────────────────────────────
    bayou["n_gate"].destinations = [
        {
            "key": "cloverfen",
            "label": "Cloverfen",
            "destination": cloverfen["e_gate"],
            "travel_description": (
                "You leave the swamp behind as the ground firms and "
                "the air clears. Neat halfling hedgerows appear ahead."
            ),
            "conditions": {"food_cost": 4},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "saltspray_bay",
            "label": "Saltspray Bay",
            "destination": saltspray["w_gate"],
            "travel_description": (
                "The coastal path leads north out of the swamp. Salt "
                "air and the cry of gulls signal Saltspray Bay."
            ),
            "conditions": {"food_cost": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Bayou S gate (EXPERT / MASTER) ─────────────────────────────────
    bayou["s_gate"].destinations = [
        {
            "key": "kashoryu",
            "label": "Kashoryu",
            "destination": kashoryu["n_gate"],
            "travel_description": (
                "You push south through thinning swamp into dense jungle. "
                "The trail grows warmer and greener until temple spires "
                "appear through the canopy."
            ),
            "conditions": {"food_cost": 4},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "aethenveil",
            "label": "Aethenveil",
            "destination": aethenveil["ne_gate"],
            "travel_description": (
                "You follow an ancient trail southwest through deepening "
                "forest. The trees grow taller and silver-barked, and the "
                "air takes on an ageless stillness."
            ),
            "conditions": {"food_cost": 4},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 10,
        },
    ]

    # ── Kashoryu N gate (EXPERT / MASTER) ──────────────────────────────
    kashoryu["n_gate"].destinations = [
        {
            "key": "bayou",
            "label": "The Bayou",
            "destination": bayou["s_gate"],
            "travel_description": (
                "The jungle trail leads north into swampland. The ground "
                "softens and strange lights flicker in the mist ahead."
            ),
            "conditions": {"food_cost": 4},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "aethenveil",
            "label": "Aethenveil",
            "destination": aethenveil["ne_gate"],
            "travel_description": (
                "You take the western trail through ancient forest. The "
                "jungle gives way to silver-barked elven woods, and "
                "carved waymarkers guide your path."
            ),
            "conditions": {"food_cost": 3},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 10,
        },
    ]

    # ── Kashoryu dock (sea routes) ─────────────────────────────────────
    kashoryu["dock"].destinations = [
        {
            "key": "teotlan_ruin",
            "label": "Teotlan Ruin",
            "destination": teotlan["dock"],
            "travel_description": "You sail north to the jungle ruins of Teotlan.",
            "conditions": {"food_cost": 3, "boat_level": 1},
            "required_cartography_tier": _BASIC,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "amber_shore",
            "label": "Amber Shore",
            "destination": amber["dock"],
            "travel_description": "You sail to the plague-touched colony of Amber Shore.",
            "conditions": {"food_cost": 3, "boat_level": 1},
            "required_cartography_tier": _BASIC,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "port_shadowmere",
            "label": "Port Shadowmere",
            "destination": shadowmere["dock"],
            "travel_description": "You sail into the perpetual twilight of Port Shadowmere.",
            "conditions": {"food_cost": 6, "boat_level": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "calenport",
            "label": "Calenport",
            "destination": calenport["dock"],
            "travel_description": "You sail to the pirate haven of Calenport.",
            "conditions": {"food_cost": 6, "boat_level": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "saltspray_bay",
            "label": "Saltspray Bay",
            "destination": saltspray["dock"],
            "travel_description": "You sail the long coastal route to Saltspray Bay.",
            "conditions": {"food_cost": 6, "boat_level": 2},
            "required_cartography_tier": _SKILLED,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "arcane_sanctum",
            "label": "The Arcane Sanctum",
            "destination": sanctum["dock"],
            "travel_description": "You sail into open ocean toward the mist-shrouded Arcane Sanctum.",
            "conditions": {"food_cost": 8, "boat_level": 3},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "oldbone_island",
            "label": "Oldbone Island",
            "destination": oldbone["dock"],
            "travel_description": "You sail to the primordial shores of Oldbone Island.",
            "conditions": {"food_cost": 8, "boat_level": 3},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "solendra",
            "label": "Solendra",
            "destination": solendra["dock"],
            "travel_description": "You sail south beyond all known charts into uncharted waters. After days at sea, a coastline of white stone and coral appears.",
            "conditions": {"food_cost": 15, "boat_level": 5},
            "required_cartography_tier": _GRANDMASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Aethenveil NE gate (MASTER) ──────────────────────────────────
    aethenveil["ne_gate"].destinations = [
        {
            "key": "bayou",
            "label": "The Bayou",
            "destination": bayou["s_gate"],
            "travel_description": (
                "You leave the ancient forest, the silver trees thinning "
                "as the trail descends into warmer, wetter country."
            ),
            "conditions": {"food_cost": 4},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "kashoryu",
            "label": "Kashoryu",
            "destination": kashoryu["n_gate"],
            "travel_description": (
                "The eastern trail leads through thinning elven forest "
                "into tropical jungle. Temple spires appear ahead."
            ),
            "conditions": {"food_cost": 3},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Aethenveil W gate (MASTER) ────────────────────────────────────
    aethenveil["w_gate"].destinations = [
        {
            "key": "shadowsward",
            "label": "The Shadowsward",
            "destination": shadowsward["s_gate"],
            "travel_description": (
                "You leave the silver forest behind and cross open "
                "country northward. The land flattens into wind-scoured "
                "grassland, and the watchtowers of the Shadowsward "
                "appear on the horizon."
            ),
            "conditions": {"food_cost": 7},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "scalded_waste",
            "label": "Scalded Waste",
            "destination": scalded_waste["n_gate"],
            "travel_description": (
                "The trail leads northwest through thinning forest into "
                "increasingly arid terrain. The ground cracks and pales "
                "as the heat builds, and soon the blistered expanse of "
                "the Scalded Waste stretches before you."
            ),
            "conditions": {"food_cost": 7},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Shadowsward S gate (EXPERT / MASTER) ──────────────────────────
    shadowsward["s_gate"].destinations = [
        {
            "key": "shadowroot",
            "label": "Shadowroot",
            "destination": shadowroot["e_gate"],
            "travel_description": (
                "You leave the frontier behind and head west into "
                "darkening forest. The trees grow twisted and blackened, "
                "their canopy blotting out the sky."
            ),
            "conditions": {"food_cost": 5},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "aethenveil",
            "label": "Aethenveil",
            "destination": aethenveil["w_gate"],
            "travel_description": (
                "You strike south across the frontier into ancient "
                "forest. The trees shift from twisted scrub to tall "
                "silver-barked sentinels, and the air takes on an "
                "ageless stillness."
            ),
            "conditions": {"food_cost": 7},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Shadowroot E gate (EXPERT / MASTER) ───────────────────────────
    shadowroot["e_gate"].destinations = [
        {
            "key": "shadowsward",
            "label": "The Shadowsward",
            "destination": shadowsward["s_gate"],
            "travel_description": (
                "You emerge from the blighted forest into open grassland. "
                "The watchtowers of the Shadowsward frontier stand ahead."
            ),
            "conditions": {"food_cost": 5},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "scalded_waste",
            "label": "Scalded Waste",
            "destination": scalded_waste["n_gate"],
            "travel_description": (
                "The trail leads south from the blighted forest into "
                "increasingly barren terrain. The ground cracks and "
                "whitens as the Scalded Waste opens before you."
            ),
            "conditions": {"food_cost": 5},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "aethenveil",
            "label": "Aethenveil",
            "destination": aethenveil["w_gate"],
            "travel_description": (
                "You head southeast through thinning blight into "
                "healthier forest. The trees gradually take on silver "
                "bark, and elven waymarkers appear along the trail."
            ),
            "conditions": {"food_cost": 7},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Scalded Waste N gate (EXPERT / MASTER) ────────────────────────
    scalded_waste["n_gate"].destinations = [
        {
            "key": "shadowroot",
            "label": "Shadowroot",
            "destination": shadowroot["e_gate"],
            "travel_description": (
                "You head north from the blistered waste into darkening "
                "forest. The blackened, twisted trees of the Shadowroot "
                "close in around you."
            ),
            "conditions": {"food_cost": 5},
            "required_cartography_tier": _EXPERT,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "aethenveil",
            "label": "Aethenveil",
            "destination": aethenveil["w_gate"],
            "travel_description": (
                "You head east from the waste, the terrain gradually "
                "greening as you enter ancient forest. Silver-barked "
                "trees and the scent of timeless air welcome you."
            ),
            "conditions": {"food_cost": 7},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Scalded Waste S gate (GRANDMASTER) ────────────────────────────
    scalded_waste["s_gate"].destinations = [
        {
            "key": "zharavan",
            "label": "Zharavan",
            "destination": zharavan["ne_gate"],
            "travel_description": (
                "You follow a barely visible trail south through the "
                "shimmering waste. The mirages part to reveal a narrow "
                "pass between sheer cliffs — and beyond it, an impossible "
                "hidden valley."
            ),
            "conditions": {"food_cost": 12},
            "required_cartography_tier": _GRANDMASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Zharavan NE gate (GRANDMASTER) ────────────────────────────────
    zharavan["ne_gate"].destinations = [
        {
            "key": "scalded_waste",
            "label": "Scalded Waste",
            "destination": scalded_waste["s_gate"],
            "travel_description": (
                "You pass through the narrow cleft in the cliffs and "
                "back into the blistered wasteland. The hidden valley "
                "vanishes behind you as if it were never there."
            ),
            "conditions": {"food_cost": 12},
            "required_cartography_tier": _GRANDMASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Sea island docks (return routes to both ports) ─────────────────
    # required_cartography_tier matches the island's tier
    _island_return_routes = {
        "teotlan_ruin": (teotlan, "Teotlan Ruin", 3, 1, _BASIC),
        "amber_shore": (amber, "Amber Shore", 3, 1, _BASIC),
        "port_shadowmere": (shadowmere, "Port Shadowmere", 6, 2, _SKILLED),
        "calenport": (calenport, "Calenport", 6, 2, _SKILLED),
        "arcane_sanctum": (sanctum, "The Arcane Sanctum", 8, 3, _EXPERT),
        "oldbone_island": (oldbone, "Oldbone Island", 8, 3, _EXPERT),
    }
    for zk, (zone, name, food, boat, carto) in _island_return_routes.items():
        zone["dock"].destinations = [
            {
                "key": "saltspray_bay",
                "label": "Saltspray Bay",
                "destination": saltspray["dock"],
                "travel_description": f"You sail from {name} back to Saltspray Bay.",
                "conditions": {"food_cost": food, "boat_level": boat},
                "required_cartography_tier": carto,
                "hidden": True, "explore_chance": 20,
            },
            {
                "key": "kashoryu",
                "label": "Kashoryu",
                "destination": kashoryu["dock"],
                "travel_description": f"You sail from {name} to the tropical harbour of Kashoryu.",
                "conditions": {"food_cost": food, "boat_level": boat},
                "required_cartography_tier": carto,
                "hidden": True, "explore_chance": 20,
            },
        ]

    # ── Solendra dock (return to Kashoryu only) ─────────────────────────
    solendra["dock"].destinations = [
        {
            "key": "kashoryu",
            "label": "Kashoryu",
            "destination": kashoryu["dock"],
            "travel_description": "You sail north from Solendra across open ocean back to the tropical harbour of Kashoryu.",
            "conditions": {"food_cost": 15, "boat_level": 5},
            "required_cartography_tier": _GRANDMASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Millholm south gate (SKILLED) ──────────────────────────────────
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
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Shadowsward NE gate (SKILLED) ────────────────────────────────
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
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
        {
            "key": "cloverfen",
            "label": "Cloverfen",
            "destination": cloverfen["nw_gate"],
            "travel_description": (
                "You head east across the frontier plains. The grass "
                "grows greener and neatly tended hedgerows appear — "
                "halfling country welcomes you."
            ),
            "conditions": {"food_cost": 3},
            "required_cartography_tier": _SKILLED,
            "hidden": True,
            "explore_chance": 20,
        },
    ]

    # ── Arcane Sanctum → Guildmere (append to existing destinations) ──
    sanctum["dock"].destinations = sanctum["dock"].destinations + [
        {
            "key": "guildmere_island",
            "label": "Guildmere Island",
            "destination": guildmere["dock"],
            "travel_description": "You sail beyond the mists toward the fabled island of Guildmere.",
            "conditions": {"food_cost": 10, "boat_level": 4},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Oldbone Island → Guildmere (append to existing destinations) ──
    oldbone["dock"].destinations = oldbone["dock"].destinations + [
        {
            "key": "guildmere_island",
            "label": "Guildmere Island",
            "destination": guildmere["dock"],
            "travel_description": "You sail from the primordial shores toward the distant gleam of Guildmere.",
            "conditions": {"food_cost": 10, "boat_level": 4},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Guildmere Island dock (MASTER / GM sea routes) ─────────────────
    guildmere["dock"].destinations = [
        {
            "key": "arcane_sanctum",
            "label": "The Arcane Sanctum",
            "destination": sanctum["dock"],
            "travel_description": "You sail from Guildmere into the mist-shrouded waters of the Arcane Sanctum.",
            "conditions": {"food_cost": 10, "boat_level": 4},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "oldbone_island",
            "label": "Oldbone Island",
            "destination": oldbone["dock"],
            "travel_description": "You sail from Guildmere to the primordial shores of Oldbone Island.",
            "conditions": {"food_cost": 10, "boat_level": 4},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
        {
            "key": "vaathari",
            "label": "Vaathari",
            "destination": vaathari["dock"],
            "travel_description": (
                "You set course across the open ocean. The crossing is "
                "long and treacherous — the sea grows dark and strange, "
                "and the stars shift overhead. After days at sea, a "
                "continent that should not exist rises from the horizon."
            ),
            "conditions": {"food_cost": 10, "boat_level": 5},
            "required_cartography_tier": _GRANDMASTER,
            "hidden": True, "explore_chance": 10,
        },
    ]

    # ── Guildmere Island N gate → Atlantis (MASTER, dive) ──────────────
    guildmere["n_gate"].destinations = [
        {
            "key": "atlantis",
            "label": "Atlantis",
            "destination": atlantis["s_gate"],
            "travel_description": (
                "You dive from the coral beach into the deep. The water "
                "is warm and impossibly clear. An underwater cave mouth "
                "yawns below, glowing with bioluminescent light. You "
                "swim down into the depths."
            ),
            "conditions": {"food_cost": 0, "water_breathing": True},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Atlantis S gate → Guildmere (MASTER) ───────────────────────────
    atlantis["s_gate"].destinations = [
        {
            "key": "guildmere_island",
            "label": "Guildmere Island",
            "destination": guildmere["n_gate"],
            "travel_description": (
                "You swim upward through the coral passage, the water "
                "brightening as you rise. The surface breaks above you "
                "and you haul yourself onto the coral beach of Guildmere."
            ),
            "conditions": {"food_cost": 0, "water_breathing": True},
            "required_cartography_tier": _MASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    # ── Vaathari dock → Guildmere (GM) ─────────────────────────────────
    vaathari["dock"].destinations = [
        {
            "key": "guildmere_island",
            "label": "Guildmere Island",
            "destination": guildmere["dock"],
            "travel_description": (
                "You set sail from the black stone quay back across the "
                "open ocean. The strange stars fade as familiar waters "
                "return, and Guildmere's white harbour appears at last."
            ),
            "conditions": {"food_cost": 10, "boat_level": 5},
            "required_cartography_tier": _GRANDMASTER,
            "hidden": True, "explore_chance": 20,
        },
    ]

    print("  All cross-zone destinations wired.")

    print("=== WORLD DEPLOY COMPLETE ===\n")


def soft_deploy_world():
    """Wipe all active zones and rebuild the full world from scratch."""
    print("=== SOFT DEPLOY WORLD ===\n")
    for zone_key in ACTIVE_ZONES:
        clean_zone(zone_key)
    deploy_world()

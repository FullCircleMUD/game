"""
Millholm Faerie Hollow — a small hidden district in the deep woods.

Builds ~5 rooms:
- Deep Woods Clearing: static midpoint between two procedural deep woods
  passages. Deliberately looks like a generic deep woods room so players
  walk through without noticing. Contains an INVISIBLE door to the hollow.
- Shimmering Threshold: transition room, the glamour lifts
- Faerie Hollow: main chamber where the fae gather
- Moonlit Glade: atmospheric side room, offerings
- Crystalline Grotto: RoomHarvesting for Arcane Dust (resource_id=16)

The entrance door is invisible (requires DETECT_INVIS to see). This is a
knowledge gate, not a level gate — the mages' guild quest provides a
detect invis scroll as a hint.

Connection points:
- deep_woods_clearing: midpoint between 4 procedural passages
  - west: proc passage 1 (inbound from deep_woods_entry in base woods)
  - west: proc passage 2 (outbound back to deep_woods_entry)
  - east: proc passage 3 (inbound to miners_camp)
  - east: proc passage 4 (outbound from miners_camp)
  (wired in build_game_world.py via DungeonTriggerExits)

Usage:
    from world.game_world.millholm_faerie_hollow import build_faerie_hollow
    build_faerie_hollow()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.exits.exit_door import ExitDoor
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from utils.exit_helpers import connect


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT_CLEARING = "millholm_deep_woods"
DISTRICT_HOLLOW = "millholm_faerie_hollow"


def build_faerie_hollow():
    """
    Build the Faerie Hollow district and the Deep Woods static clearing.

    Returns:
        dict of room key → room object. Key rooms for cross-district
        connections: 'deep_woods_clearing' (midpoint between procedural
        deep woods passages).
    """
    rooms = {}

    # ══════════════════════════════════════════════════════════════════
    # 1. CREATE ROOMS
    # ══════════════════════════════════════════════════════════════════

    # ── Deep Woods Clearing (static midpoint) ─────────────────────────
    # This room sits between two procedural deep woods passages.
    # It MUST look like a generic deep woods room — players should walk
    # straight through without realising they've entered a static room.
    # The invisible door to the faerie hollow is the only clue.

    rooms["deep_woods_clearing"] = create_object(
        RoomBase,
        key="Deep Woods",
        attributes=[
            ("desc",
             "Ancient trees press close, their trunks thick with moss "
             "and their branches woven into an unbroken canopy far "
             "overhead. The undergrowth is dense and dark, choked with "
             "fern and shadow. The air is heavy, still, and smells of "
             "damp earth and decay. There is nothing to distinguish "
             "this stretch of forest from any other."),
        ],
    )

    # ── Shimmering Threshold ──────────────────────────────────────────

    rooms["shimmering_threshold"] = create_object(
        RoomBase,
        key="Shimmering Threshold",
        attributes=[
            ("desc",
             "The forest changes in a single step. The oppressive gloom "
             "of the deep woods lifts and the air turns warm, sweet, "
             "and faintly luminous. Motes of soft light drift between "
             "the trees like lazy fireflies, and the leaves overhead "
             "glow with a pale silver-green radiance that has nothing "
             "to do with the sun. The ground is carpeted with moss so "
             "vivid it seems to pulse with life. Birdsong — impossibly "
             "clear and melodic — echoes from somewhere ahead."),
        ],
    )
    rooms["shimmering_threshold"].details = {
        "light": (
            "The motes of light drift with apparent purpose, circling "
            "gently before floating onward. They are warm to the touch "
            "and leave a faint tingling on the skin. Not insects — "
            "something else entirely."
        ),
        "moss": (
            "The moss is impossibly green, thick as velvet, and cool "
            "underfoot. No twig or leaf mars its surface. It grows in "
            "perfect, unbroken sheets across the ground, as though "
            "tended by careful hands."
        ),
    }

    # ── Faerie Hollow ─────────────────────────────────────────────────

    rooms["faerie_hollow"] = create_object(
        RoomBase,
        key="Faerie Hollow",
        attributes=[
            ("desc",
             "A wide, bowl-shaped clearing opens beneath a cathedral "
             "of ancient oaks whose branches arch overhead like the "
             "ribs of a living vault. Silver light pools in the hollow, "
             "cast by no visible source. Rings of pale mushrooms mark "
             "concentric circles in the moss, and tiny flowers — white, "
             "blue, violet — bloom in defiance of season. The air hums "
             "with a low, resonant vibration, felt in the bones more "
             "than heard. Small winged shapes flit between the branches, "
             "too quick to focus on, trailing sparks of light."),
        ],
    )
    rooms["faerie_hollow"].details = {
        "mushrooms": (
            "The mushrooms are pale as bone and perfectly formed, each "
            "one identical to the last. They grow in concentric rings, "
            "the outermost nearly ten feet across. Stepping into the "
            "innermost ring makes the humming grow louder."
        ),
        "flowers": (
            "Tiny blossoms in white, blue, and deep violet grow in "
            "clusters that seem to spell out patterns — or perhaps "
            "that's just the light playing tricks. They have no scent "
            "that a human nose can detect, but they vibrate faintly "
            "when touched."
        ),
        "shapes": (
            "The winged shapes move too fast to see clearly — a flash "
            "of iridescent wing, a glimpse of a face no larger than "
            "a thumbnail, a peal of laughter like tiny bells. They "
            "watch you with evident curiosity."
        ),
    }

    # ── Moonlit Glade ─────────────────────────────────────────────────

    rooms["moonlit_glade"] = create_object(
        RoomBase,
        key="Moonlit Glade",
        attributes=[
            ("desc",
             "A quiet glade bathed in perpetual moonlight, though the "
             "sky above is only leaves and branches. A flat stone, "
             "waist-high and smoothed by countless hands, stands at "
             "the center — an altar or offering table. Small gifts "
             "have been placed upon it: a polished acorn, a coil of "
             "silver wire, a perfect apple. The air here is calm and "
             "expectant, as though the glade itself is waiting."),
        ],
    )
    rooms["moonlit_glade"].details = {
        "stone": (
            "The stone is pale granite, worn satin-smooth on its upper "
            "surface. Faint grooves suggest it was once carved, but "
            "centuries of offerings and touching hands have erased all "
            "detail. It radiates a gentle warmth."
        ),
        "gifts": (
            "Small tokens left by previous visitors — or perhaps by the "
            "fae themselves. A polished acorn, a twist of silver wire, "
            "a perfect red apple with no sign of decay, a white feather, "
            "a river stone with a hole worn through its center."
        ),
        "altar": (
            "The stone is pale granite, worn satin-smooth on its upper "
            "surface. Faint grooves suggest it was once carved, but "
            "centuries of offerings and touching hands have erased all "
            "detail. It radiates a gentle warmth."
        ),
    }

    # ── Crystalline Grotto (Arcane Dust harvest) ──────────────────────

    rooms["crystalline_grotto"] = create_object(
        RoomHarvesting,
        key="Crystalline Grotto",
        attributes=[
            ("desc",
             "A shallow cave behind a curtain of hanging roots, its "
             "walls studded with pale crystals that pulse with a soft "
             "inner light. The crystals grow in clusters like frozen "
             "flowers, their facets throwing tiny rainbows across the "
             "stone. A fine, glittering dust — arcane residue shed by "
             "the crystals — coats every surface. The air tastes of "
             "ozone and something sweeter, like distant lightning over "
             "a meadow."),
            ("resource_id", 16),
            ("resource_count", 0),
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "gather"),
            ("desc_abundant",
             "Glittering arcane dust coats the crystals and collects "
             "in the crevices of the stone. There is plenty to "
             "'gather'."),
            ("desc_scarce",
             "Most of the loose dust has been collected. A thin film "
             "still clings to the deeper crevices to 'gather'."),
            ("desc_depleted",
             "The crystals have been swept clean of dust. It will take "
             "time for them to shed more."),
        ],
    )
    rooms["crystalline_grotto"].details = {
        "crystals": (
            "The crystals are translucent and faintly warm, pulsing "
            "with a rhythm like a slow heartbeat. They grow directly "
            "from the stone, as natural as quartz but resonating with "
            "magical energy. Breaking one would be unwise — and the "
            "fae would not forgive it."
        ),
        "dust": (
            "Fine as flour and faintly luminous, the arcane dust is "
            "shed naturally by the crystals as they grow. It clings "
            "to the fingers and glows briefly when disturbed. This is "
            "a key ingredient in potions and enchantments."
        ),
    }

    print(f"  Created {len(rooms)} rooms.")

    # ══════════════════════════════════════════════════════════════════
    # 2. CREATE EXITS
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # ── Invisible door: clearing → threshold ──────────────────────────
    # One-way invisible door from clearing into the hollow. The return
    # exit from threshold back to clearing is normal (visible) — once
    # you're inside, you can leave freely.

    invis_door = create_object(
        ExitDoor,
        key="a shimmer in the air",
        location=rooms["deep_woods_clearing"],
        destination=rooms["shimmering_threshold"],
    )
    invis_door.set_direction("north")
    invis_door.door_name = "shimmer"
    invis_door.is_open = True       # no need to open it, just walk through
    invis_door.is_invisible = True   # requires DETECT_INVIS to see
    invis_door.aliases.add("shimmer")
    exit_count += 1

    # Return exit (visible — you can always leave)
    exit_back = create_object(
        ExitVerticalAware,
        key="Deep Woods",
        location=rooms["shimmering_threshold"],
        destination=rooms["deep_woods_clearing"],
    )
    exit_back.set_direction("south")
    exit_count += 1

    # ── Hollow interior connections ───────────────────────────────────
    connect(rooms["shimmering_threshold"], rooms["faerie_hollow"], "north")
    connect(rooms["faerie_hollow"], rooms["moonlit_glade"], "west")
    connect(rooms["faerie_hollow"], rooms["crystalline_grotto"], "east")
    exit_count += 6

    print(f"  Created {exit_count} exits.")

    # ══════════════════════════════════════════════════════════════════
    # 3. TAG ROOMS — zone, district, terrain
    # ══════════════════════════════════════════════════════════════════

    # The clearing is deep woods district
    rooms["deep_woods_clearing"].tags.add(ZONE, category="zone")
    rooms["deep_woods_clearing"].tags.add(DISTRICT_CLEARING, category="district")
    rooms["deep_woods_clearing"].set_terrain(TerrainType.FOREST.value)

    # The hollow rooms are their own district
    hollow_keys = [
        "shimmering_threshold", "faerie_hollow",
        "moonlit_glade", "crystalline_grotto",
    ]
    for key in hollow_keys:
        rooms[key].tags.add(ZONE, category="zone")
        rooms[key].tags.add(DISTRICT_HOLLOW, category="district")
        rooms[key].set_terrain(TerrainType.FOREST.value)

    print("  Tagged all rooms with zone, district, and terrain.")

    # ══════════════════════════════════════════════════════════════════
    # 4. FUTURE CONNECTION NOTES
    # ══════════════════════════════════════════════════════════════════
    # 4 procedural passages connect through this district:
    #   1. deep_woods_entry → deep_woods_clearing (inbound from base woods)
    #   2. deep_woods_clearing → deep_woods_entry (outbound, return)
    #   3. deep_woods_clearing → miners_camp (inbound to mine)
    #   4. miners_camp → deep_woods_clearing (outbound from mine)
    # deep_woods_clearing: west = proc passage arrival/departure
    #                      east = proc passage to/from mine
    #                      north = invisible door to faerie hollow
    # faerie_hollow: future faerie NPC spawns, gift/quest mechanics
    # moonlit_glade: offering altar — future quest interaction point

    # ── District map cell tags ────────────────────────────────────────
    # deep_woods_clearing is the shared region "deep_woods" marker —
    # both this room and the miners_camp reveal the same vague cell.
    rooms["deep_woods_clearing"].tags.add("millholm_region:deep_woods", category="map_cell")
    print("  Tagged deep_woods_clearing with millholm_region:deep_woods map_cell tag.")

    print("  Millholm Faerie Hollow complete.\n")
    return rooms


from evennia import create_object, ObjectDB

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from utils.exit_helpers import connect_bidirectional_exit


def _create_arena_room(key, desc):
    """Create a single arena room with PVP flags enabled."""
    return create_object(
        RoomBase,
        key=key,
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("allow_combat", True),
            ("allow_pvp", True),
            ("allow_death", False),
            ("desc", desc),
        ],
    )


def test_area_arena():
    """
    Builds a 9-room gladiatorial arena.

    PVP and combat flags are enabled in every room.

    Layout (3x3 grid):

        NW --- N --- NE
        |      |      |
        W  - Centre - E
        |      |      |
        SW --- S --- SE

    Connected north from Limbo.
    """

    # Find Limbo to connect to
    results = ObjectDB.objects.filter(db_key="Limbo")
    if not results:
        print("  ERROR: Limbo not found — skipping arena")
        return
    limbo = results[0]

    ##########################
    # Arena — 9 rooms in a 3x3 grid
    ##########################

    nw = _create_arena_room(
        "The Arena (Northwest)",
        "The northwest corner of the arena floor. A thick stone pillar rises "
        "here, its surface scarred by sword strikes and axe blows. Blood-stained "
        "sand crunches underfoot. The roar of the crowd echoes off the high walls.",
    )

    n = _create_arena_room(
        "The Arena (North)",
        "The northern stretch of the arena floor. A heavy iron portcullis is "
        "set into the wall here — beyond it, a dark passage leads to the "
        "gladiator holding cells. The sand is churned and trampled.",
    )

    ne = _create_arena_room(
        "The Arena (Northeast)",
        "The northeast corner of the arena. Heavy iron doors lead to the beast "
        "cages — deep claw marks score the flagstones where creatures have been "
        "dragged into the ring. A feral smell lingers in the air.",
    )

    w = _create_arena_room(
        "The Arena (West)",
        "The western edge of the arena floor. Weapon racks line the wall, "
        "holding dulled training blades and battered shields for combatants "
        "who arrive unprepared. The sand here is freshly raked.",
    )

    centre = _create_arena_room(
        "The Arena (Centre)",
        "The heart of the arena. The sand here is darkest — stained by "
        "countless bouts. A painted circle marks the centre of the fighting "
        "pit. The crowd's roar is loudest here, reverberating from every wall.",
    )

    e = _create_arena_room(
        "The Arena (East)",
        "The eastern edge of the arena floor. Water troughs and buckets sit "
        "against the wall for combatants to drink between rounds. A bloodied "
        "sand pit nearby serves for warm-up bouts.",
    )

    sw = _create_arena_room(
        "The Arena (Southwest)",
        "The southwest corner of the arena, near the pit master's booth. "
        "A scarred wooden desk holds ledgers of wagers and fight records. "
        "The pit master's whip hangs from a hook on the wall.",
    )

    s = _create_arena_room(
        "The Arena (South)",
        "The southern stretch of the arena floor. The main gate looms behind "
        "you — a massive iron-banded door through which combatants enter to "
        "the deafening cheers of the crowd above.",
    )

    se = _create_arena_room(
        "The Arena (Southeast)",
        "The southeast corner of the arena. A trophy wall displays the names "
        "and weapons of past champions. Faded bloodstains beneath each plaque "
        "tell their own stories.",
    )

    # --- Grid connections (N/S/E/W only, no diagonals) ---

    # Top row (east/west)
    connect_bidirectional_exit(nw, n, "east")
    connect_bidirectional_exit(n, ne, "east")

    # Middle row (east/west)
    connect_bidirectional_exit(w, centre, "east")
    connect_bidirectional_exit(centre, e, "east")

    # Bottom row (east/west)
    connect_bidirectional_exit(sw, s, "east")
    connect_bidirectional_exit(s, se, "east")

    # Left column (north/south)
    connect_bidirectional_exit(nw, w, "south")
    connect_bidirectional_exit(w, sw, "south")

    # Middle column (north/south)
    connect_bidirectional_exit(n, centre, "south")
    connect_bidirectional_exit(centre, s, "south")

    # Right column (north/south)
    connect_bidirectional_exit(ne, e, "south")
    connect_bidirectional_exit(e, se, "south")

    # --- Arena Infirmary (defeat destination) ---
    infirmary = create_object(
        RoomBase,
        key="The Arena Infirmary",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("allow_combat", False),
            ("allow_pvp", False),
            ("allow_death", False),
            ("desc",
             "A low-ceilinged chamber off the arena floor, smelling of poultice "
             "and old blood. Straw pallets line the walls where defeated "
             "combatants are brought to recover. A grizzled healer sits on a "
             "stool, stitching a gash on a groaning gladiator's arm."),
        ],
    )
    # Wire all arena rooms to send defeated characters here
    for room in [nw, n, ne, w, centre, e, sw, s, se]:
        room.defeat_destination = infirmary

    # Connect infirmary to the south room (main entrance area)
    connect_bidirectional_exit(s, infirmary, "west")

    # --- Connect to main world ---
    connect_bidirectional_exit(limbo, s, "north")

    ##########################
    # Zone and District tags
    ##########################

    all_arena_rooms = [nw, n, ne, w, centre, e, sw, s, se, infirmary]
    for room in all_arena_rooms:
        room.tags.add("arena_zone", category="zone")

    for room in [nw, n, ne, w, centre, e, sw, s, se]:
        room.tags.add("arena_district", category="district")

    infirmary.tags.add("infirmary_district", category="district")

    # --- Terrain types ---
    for room in all_arena_rooms:
        room.set_terrain(TerrainType.URBAN.value)

    print("Test Arena (3x3 PVP + Infirmary) Created")

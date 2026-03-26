
from evennia import ObjectDB, create_object, search_object

# Import your typeclasses
from world.test_world.test_area_beach import test_area_beach
from world.test_world.test_area_economic import test_area_economic
from world.test_world.test_area_arena import test_area_arena
from world.test_world.test_area_combat import test_area_combat
from world.test_world.spawn_test_items import spawn_test_items
from world.test_world.spawn_npcs import spawn_npcs
from typeclasses.scripts.zone_spawn_script import ZoneSpawnScript
from world.test_world.test_area_dungeon import test_area_dungeon
from world.test_world.test_area_gateway import test_area_gateway
from world.test_world.test_area_castle_wall import test_area_castle_wall


RECYCLE_BIN_KEY = "nft_recycle_bin"
PURGATORY_KEY = "Purgatory"
CEMETERY_KEY = "Cemetery"


def _ensure_recycle_bin():
    """Create the NFT recycle bin room if it doesn't already exist."""
    existing = search_object(RECYCLE_BIN_KEY, exact=True)
    if existing:
        print(f"  RecycleBin already exists: {existing[0].dbref}")
        return existing[0]

    room = create_object(
        "typeclasses.terrain.rooms.room_recycle_bin.RoomRecycleBin",
        key=RECYCLE_BIN_KEY,
    )
    room.locks.add("teleport:false();traverse:false()")
    room.db.desc = "A hidden room where orphaned NFT items are despawned and recycled."
    print(f"  Created RecycleBin: {room.dbref}")
    return room


def _ensure_purgatory():
    """Create the purgatory room if it doesn't already exist."""
    existing = search_object(PURGATORY_KEY, exact=True)
    if existing:
        print(f"  Purgatory already exists: {existing[0].dbref}")
        return existing[0]

    room = create_object(
        "typeclasses.terrain.rooms.room_purgatory.RoomPurgatory",
        key=PURGATORY_KEY,
    )
    room.locks.add("teleport:false();traverse:false()")
    print(f"  Created Purgatory: {room.dbref}")
    return room


def _ensure_cemetery():
    """Create the cemetery room if it doesn't already exist."""
    existing = search_object(CEMETERY_KEY, exact=True)
    if existing:
        print(f"  Cemetery already exists: {existing[0].dbref}")
        return existing[0]

    room = create_object(
        "typeclasses.terrain.rooms.room_cemetery.RoomCemetery",
        key=CEMETERY_KEY,
    )
    room.db.desc = (
        "Weathered gravestones and crumbling monuments dot this quiet clearing. "
        "A faint mist clings to the ground, and the air is still. "
        "This is a place of rest — and of new beginnings."
    )
    print(f"  Created Cemetery: {room.dbref}")
    return room


def build_test_world():

    # start the world scripts

    # create the NFT recycle bin (must exist before spawning items)
    recycle_bin = _ensure_recycle_bin()

    # create death system rooms (purgatory + cemetery)
    purgatory = _ensure_purgatory()
    _ensure_cemetery()

    # Tag system rooms
    for room in [recycle_bin, purgatory]:
        room.tags.add("system_zone", category="zone")
        room.tags.add("system_district", category="district")

    # build the test areas
    test_area_beach()
    test_area_economic()
    test_area_arena()

    # spawn NFT items and fungibles into rooms
    spawn_test_items()
    test_area_combat()

    # spawn NPCs (trainers, shopkeepers, etc.)
    spawn_npcs()

    # create zone spawn script (rabbits, wolves, dire wolf auto-managed)
    ZoneSpawnScript.create_for_zone("test_economic_zone")

    # spawn dungeon entrance (requires economic area for Thieves Guild)
    test_area_dungeon()

    # spawn gateway rooms linking zones (requires all areas)
    test_area_gateway()

    # height adapter test areas
    test_area_castle_wall()



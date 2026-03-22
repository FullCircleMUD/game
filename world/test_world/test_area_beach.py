
from evennia import create_object
from evennia import ObjectDB

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from utils.exit_helpers import connect


def test_area_beach():
    """
    Builds the beach/ocean test area for swimming and flying tests.
    """

    limbo = ObjectDB.objects.get(id=2)

    ocean = create_object(
        RoomBase,
        key="ocean",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc", "the long deep swells roll by, you can just glimpse what looks like land on the horizen to the north")
        ]
    )

    coastal = create_object(
        RoomBase,
        key="coastal",
        attributes=[
            ("max_height", 1),
            ("max_depth", -1),
            ("desc", "the breakers roll up toward the beach, don't let the waves dump you")
        ]
    )

    beach = create_object(
        RoomBase,
        key="beach",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this white sand beach stretches from the breaking waves to a small beach hut just north")
        ]
    )

    cabin = create_object(
        RoomBase,
        key="cabin",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "the inside of this small cabin made of driftwood and palm fronds smells damp and mouldy.")
        ]
    )

    # --- Exits ---
    connect(limbo, beach, "west", desc_ab="white sand beach", desc_ba="Limbo")
    connect(beach, cabin, "north", desc_ab="small beach cabin", desc_ba="door to the beach")
    connect(beach, coastal, "south", desc_ab="rolling surf", desc_ba="white sand beach")
    connect(coastal, ocean, "south", desc_ab="deep rolling ocean", desc_ba="the breaking waves")

    ##########################
    # Zone and District tags
    ##########################

    for room in [ocean, coastal, beach, cabin]:
        room.tags.add("test_water_fly_zone", category="zone")

    for room in [beach, cabin]:
        room.tags.add("beach_district", category="district")

    for room in [coastal, ocean]:
        room.tags.add("ocean_district", category="district")

    # --- Terrain types ---
    for room in [beach, cabin]:
        room.set_terrain(TerrainType.COASTAL.value)
    for room in [coastal, ocean]:
        room.set_terrain(TerrainType.WATER.value)

    print("Test Beach Area Created")

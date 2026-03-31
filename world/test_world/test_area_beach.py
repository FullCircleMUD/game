
from evennia import create_object
from evennia import ObjectDB

from enums.terrain_type import TerrainType
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.terrain.rooms.room_base import RoomBase
from utils.exit_helpers import connect_bidirectional_exit


def test_area_beach():
    """
    Builds the beach/ocean test area for swimming and flying tests.

    Includes a height-routed exit demonstration:
      ocean → south at heights -1, 0, 1 → deep ocean (another ocean room)
      ocean → south at height -2         → underwater cave (air pocket)
    """

    limbo = ObjectDB.objects.get(id=2)

    ocean = create_object(
        RoomBase,
        key="ocean",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc", "the long deep swells roll by, you can just glimpse "
             "what looks like land on the horizen to the north")
        ]
    )

    coastal = create_object(
        RoomBase,
        key="coastal",
        attributes=[
            ("max_height", 1),
            ("max_depth", -1),
            ("desc", "the breakers roll up toward the beach, don't let "
             "the waves dump you")
        ]
    )

    beach = create_object(
        RoomBase,
        key="beach",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this white sand beach stretches from the breaking "
             "waves to a small beach hut just north")
        ]
    )

    cabin = create_object(
        RoomBase,
        key="cabin",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "the inside of this small cabin made of driftwood "
             "and palm fronds smells damp and mouldy.")
        ]
    )

    # ── Height-routed rooms south of ocean ─────────────────────────
    # Same direction (south), different destinations based on depth.
    # Heights -1, 0, 1 → deep_ocean (more open water)
    # Height -2         → underwater_cave (air pocket cave)

    deep_ocean = create_object(
        RoomBase,
        key="Deep Ocean",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc", "The ocean stretches endlessly in every direction. "
             "The water is dark and deep here, the swells enormous. "
             "Far below, the seabed is lost in shadow.")
        ]
    )

    underwater_cave = create_object(
        RoomBase,
        key="Underwater Cave",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "You surface inside a small air pocket within a "
             "rocky cave. Bioluminescent algae clings to the walls, "
             "casting an eerie blue-green glow. The water laps at "
             "a narrow ledge of smooth stone. The only way out is "
             "back down through the submerged passage you came from.")
        ]
    )

    # --- Exits ---
    connect_bidirectional_exit(limbo, beach, "west", desc_ab="white sand beach", desc_ba="Limbo")
    connect_bidirectional_exit(beach, cabin, "north", desc_ab="small beach cabin", desc_ba="door to the beach")
    connect_bidirectional_exit(beach, coastal, "south", desc_ab="rolling surf", desc_ba="white sand beach")
    connect_bidirectional_exit(coastal, ocean, "south", desc_ab="deep rolling ocean", desc_ba="the breaking waves")

    # Height-routed exits from ocean south:
    # Exit 1: surface/shallow/flying → deep ocean
    exit_to_deep = create_object(
        ExitVerticalAware,
        key="Deep Ocean",
        location=ocean,
        destination=deep_ocean,
    )
    exit_to_deep.set_direction("south")
    exit_to_deep.required_min_height = -1  # depth -1 through flying
    # No required_max_height — any height from -1 upward

    # Exit 2: deep dive → underwater cave (only at depth -2)
    exit_to_cave = create_object(
        ExitVerticalAware,
        key="a dark opening in the rocks",
        location=ocean,
        destination=underwater_cave,
    )
    exit_to_cave.set_direction("south")
    exit_to_cave.required_min_height = -2
    exit_to_cave.required_max_height = -2
    # Arrival at ground level inside the air pocket cave
    exit_to_cave.arrival_heights = {-2: 0}

    # Return exit from deep ocean back to ocean
    exit_deep_back = create_object(
        ExitVerticalAware,
        key="ocean",
        location=deep_ocean,
        destination=ocean,
    )
    exit_deep_back.set_direction("north")

    # Return exit from underwater cave back to ocean (at depth -2)
    exit_cave_back = create_object(
        ExitVerticalAware,
        key="the submerged passage",
        location=underwater_cave,
        destination=ocean,
    )
    exit_cave_back.set_direction("north")
    exit_cave_back.arrival_heights = {0: -2}  # emerge at depth -2

    ##########################
    # Zone and District tags
    ##########################

    for room in [ocean, coastal, beach, cabin, deep_ocean, underwater_cave]:
        room.tags.add("test_water_fly_zone", category="zone")

    for room in [beach, cabin]:
        room.tags.add("beach_district", category="district")

    for room in [coastal, ocean, deep_ocean]:
        room.tags.add("ocean_district", category="district")

    underwater_cave.tags.add("ocean_district", category="district")

    # --- Terrain types ---
    for room in [beach, cabin]:
        room.set_terrain(TerrainType.COASTAL.value)
    for room in [coastal, ocean, deep_ocean]:
        room.set_terrain(TerrainType.WATER.value)
    underwater_cave.set_terrain(TerrainType.UNDERGROUND.value)
    underwater_cave.always_lit = True  # bioluminescent algae

    print("Test Beach Area Created")
    print("  Height-routed exits from ocean:")
    print("    south at surface/shallow/flying → Deep Ocean")
    print("    south at depth -2 → Underwater Cave (air pocket)")

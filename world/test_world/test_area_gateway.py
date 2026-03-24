"""
Spawn gateway rooms connecting the test zones.

Run AFTER test_area_economic and test_area_beach have created their rooms.

Creates:
  1. Overland gateway pair:
     Economic Zone (dt6) <-> Beach Zone (cabin) — food cost: 1 bread
  2. Dock gateway pair (sea route):
     The Town Dock (off dt6) <-> The Beach Dock (off beach) — BASIC ship + 1 bread

Usage (from Evennia):
    @py from world.test_world.test_area_gateway import test_area_gateway; test_area_gateway()
"""

from evennia import ObjectDB, create_object

from enums.room_crafting_type import RoomCraftingType
from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_crafting import RoomCrafting
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect


def _find_room(key):
    """Find a room by exact key."""
    results = ObjectDB.objects.filter(db_key=key, db_typeclass_path__contains="room")
    if results.exists():
        return results.first()
    return None


def test_area_gateway():
    """Spawn gateway rooms linking test zones."""

    print("\n=== Spawning Gateway Rooms ===\n")

    # ── Find anchor rooms ──────────────────────────────────────────
    dt6 = _find_room("dirt track 6")
    if not dt6:
        print("  ! dirt track 6 not found — run test_area_economic() first")
        return

    cabin = _find_room("cabin")
    if not cabin:
        print("  ! cabin not found — run test_area_beach() first")
        return

    # ── Gateway: Economic (dt6) <-> Beach (cabin) ─────────────────
    bush_track = _find_room("The Bush Track")
    coastal_trail = _find_room("The Coastal Trail")

    if not bush_track:
        bush_track = create_object(
            RoomGateway,
            key="The Bush Track",
        )
        bush_track.db.desc = (
            "A narrow track leads north through dense scrub. The air "
            "is thick with the buzz of insects and the smell of eucalyptus. "
            "A faded blaze mark on a tree trunk points the way."
        )
        bush_track.tags.add("test_economic_zone", category="zone")
        bush_track.tags.add("resource_district", category="district")
        bush_track.set_terrain(TerrainType.FOREST.value)
        print(f"  Created gateway: The Bush Track {bush_track.dbref}")

        connect(dt6, bush_track, "north",
                desc_ab="a narrow bush track", desc_ba="dirt track 6")
    else:
        print(f"  Bush Track already exists: {bush_track.dbref}")

    if not coastal_trail:
        coastal_trail = create_object(
            RoomGateway,
            key="The Coastal Trail",
        )
        coastal_trail.db.desc = (
            "A sandy trail winds down through low dunes toward a "
            "small cabin. The crash of waves echoes from the south "
            "and salt spray hangs in the air."
        )
        coastal_trail.tags.add("test_water_fly_zone", category="zone")
        coastal_trail.tags.add("beach_district", category="district")
        coastal_trail.set_terrain(TerrainType.COASTAL.value)
        print(f"  Created gateway: The Coastal Trail {coastal_trail.dbref}")

        connect(cabin, coastal_trail, "north",
                desc_ab="a coastal trail", desc_ba="small beach cabin")
    else:
        print(f"  Coastal Trail already exists: {coastal_trail.dbref}")

    # Wire the gateway pair
    bush_track.destinations = [
        {
            "key": "beach",
            "label": "The Coastal Trail",
            "destination": coastal_trail,
            "travel_description": (
                "You push through the dense bush, ducking under low "
                "branches. The scrub thins and the ground turns sandy. "
                "Soon the sound of waves reaches your ears."
            ),
            "conditions": {"food_cost": 1},
            "hidden": True,
        },
    ]
    coastal_trail.destinations = [
        {
            "key": "economic",
            "label": "The Bush Track",
            "destination": bush_track,
            "travel_description": (
                "You leave the coast behind and head inland along "
                "a narrow track. The scrub closes in around you "
                "before opening onto a dusty dirt road."
            ),
            "conditions": {"food_cost": 1},
            "hidden": True,
        },
    ]
    print("  Linked: Bush Track <-> Coastal Trail (1 bread)")

    # ── Docks: Economic (dt6) <-> Beach (beach) — sea route ─────────
    beach = _find_room("beach")
    if not beach:
        print("  ! beach not found — run test_area_beach() first")
        return

    town_dock = _find_room("The Town Dock")
    beach_dock = _find_room("The Beach Dock")

    if not town_dock:
        town_dock = create_object(
            RoomGateway,
            key="The Town Dock",
        )
        town_dock.db.desc = (
            "A sturdy wooden jetty juts out over the water. Small fishing "
            "boats bob alongside, and the air smells of salt and tar. "
            "A weathered post marks the departure point for sea voyages."
        )
        town_dock.tags.add("test_economic_zone", category="zone")
        town_dock.tags.add("resource_district", category="district")
        town_dock.set_terrain(TerrainType.COASTAL.value)
        print(f"  Created dock: The Town Dock {town_dock.dbref}")

        connect(dt6, town_dock, "south",
                desc_ab="a wooden jetty", desc_ba="dirt track 6")
    else:
        print(f"  Town Dock already exists: {town_dock.dbref}")

    if not beach_dock:
        beach_dock = create_object(
            RoomGateway,
            key="The Beach Dock",
        )
        beach_dock.db.desc = (
            "A rough timber dock extends from the sand into the shallows. "
            "Waves lap against the pilings and a rope cleat stands ready "
            "to receive a mooring line."
        )
        beach_dock.tags.add("test_water_fly_zone", category="zone")
        beach_dock.tags.add("beach_district", category="district")
        beach_dock.set_terrain(TerrainType.COASTAL.value)
        print(f"  Created dock: The Beach Dock {beach_dock.dbref}")

        connect(beach, beach_dock, "west",
                desc_ab="a rough timber dock", desc_ba="white sand beach")
    else:
        print(f"  Beach Dock already exists: {beach_dock.dbref}")

    # Wire the dock pair — requires a BASIC-tier ship (boat_level=1)
    town_dock.destinations = [
        {
            "key": "beach_dock",
            "label": "The Beach Dock",
            "destination": beach_dock,
            "travel_description": (
                "You cast off from the jetty and sail along the coast. "
                "The town shrinks behind you as the open water stretches "
                "ahead. Before long, a sandy beach comes into view."
            ),
            "conditions": {"boat_level": 1, "food_cost": 1},
            "hidden": True,
        },
    ]
    beach_dock.destinations = [
        {
            "key": "town_dock",
            "label": "The Town Dock",
            "destination": town_dock,
            "travel_description": (
                "You weigh anchor and sail back along the coast. "
                "The familiar outline of the town dock grows larger "
                "as you approach, and you tie off at the jetty."
            ),
            "conditions": {"boat_level": 1, "food_cost": 1},
            "hidden": True,
        },
    ]
    print("  Linked: Town Dock <-> Beach Dock (BASIC ship + 1 bread)")

    # ── Shipyard: east of Town Dock — test crafting room ──────────
    shipyard = _find_room("The Shipyard")
    if not shipyard:
        shipyard = create_object(
            RoomCrafting,
            key="The Shipyard",
        )
        shipyard.db.desc = (
            "A sprawling open-air workshop dominates the waterfront. Timber "
            "frames rise like the ribs of great beasts, and the air is thick "
            "with the smell of pitch and fresh-cut wood. Heavy chains dangle "
            "from overhead cranes, and workers' tools line the walls."
        )
        shipyard.db.crafting_type = RoomCraftingType.SHIPYARD.value
        shipyard.db.mastery_level = 5  # up to GRANDMASTER
        shipyard.db.craft_cost = 10
        shipyard.tags.add("test_economic_zone", category="zone")
        shipyard.tags.add("resource_district", category="district")
        shipyard.set_terrain(TerrainType.COASTAL.value)
        shipyard.db.always_lit = True
        print(f"  Created shipyard: The Shipyard {shipyard.dbref}")

        connect(town_dock, shipyard, "east",
                desc_ab="a sprawling shipyard", desc_ba="the town dock")
    else:
        print(f"  Shipyard already exists: {shipyard.dbref}")

    print("\n=== Gateway Rooms Done ===\n")

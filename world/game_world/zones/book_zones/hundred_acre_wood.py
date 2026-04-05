"""
Hundred Acre Wood — book zone accessed from the Millholm Public Library.

A 7-column x 8-row grid of rooms based on the classic Winnie the Pooh
setting, plus houses off the edges and vertical rooms.

Usage (Evennia shell):
    from world.game_world.zones.book_zones.hundred_acre_wood import (
        build_hundred_acre_wood, clean_hundred_acre_wood
    )
    build_hundred_acre_wood()
    clean_hundred_acre_wood()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from utils.exit_helpers import connect_bidirectional_exit, connect_bidirectional_door_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE = "book_hundred_acre_wood"
DISTRICT = "hundred_acre_wood"


def clean_hundred_acre_wood():
    """Remove all Hundred Acre Wood zone objects."""
    _clean_zone(ZONE)


def build_hundred_acre_wood():
    """
    Build the Hundred Acre Wood and return gateway rooms dict.

    Returns:
        dict with "entry" key pointing to the entrance room.
    """
    print("=== BUILDING HUNDRED ACRE WOOD (Book Zone) ===\n")

    rooms = {}

    # ==================================================================
    #  ROW 0 — Entrance
    # ==================================================================

    rooms["entrance"] = create_object(
        RoomBase,
        key="Entrance to the Hundred Acre Wood",
        attributes=[
            ("desc",
             "You are standing at the entrance to a large woods. It looks "
             "like something out of a child's imagination. You can hear "
             "bees buzzing, animals frolicking and occasionally a silly "
             "bouncing noise. There is a sign here and to the north is "
             "the entrance."),
        ],
    )

    # ==================================================================
    #  ROW 1 — Bottom row
    # ==================================================================

    rooms["r1c1"] = create_object(
        RoomBase,
        key="Floody Place",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. This area looks "
             "like it is frequently flooded, and the ground is very mushy."),
        ],
    )

    rooms["r1c2"] = create_object(
        RoomBase,
        key="Where the Woozle Wasn't",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. This is where "
             "the Woozle wasn't but he might be now."),
        ],
    )

    rooms["r1c3"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing just inside the Hundred Acre Wood. You can "
             "hear birds chirping and little animals scurrying. The Hollow "
             "Log is to the north. The Floody Place is to the west and "
             "Eeyores Gloomy Place is to the east."),
        ],
    )

    rooms["r1c4"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. This is such a "
             "lovely little woods and you get the feeling you belong here. "
             "For some reason you can't get the Pooh Song out of your head."),
        ],
    )

    rooms["r1c5"] = create_object(
        RoomBase,
        key="Eeyore's Gloomy Place",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. This is where "
             "Eeyore lives. You see a small lean-to here that you assume "
             "is Eeyores home. Gosh, this is such a gloomy place!"),
        ],
    )

    # ==================================================================
    #  ROW 2
    # ==================================================================

    rooms["piglet_house"] = create_object(
        RoomBase,
        key="Piglet's House",
        attributes=[
            ("desc",
             "You are standing inside a small house. There is not much of "
             "interest here, but then Piglet is not very interesting."),
        ],
    )

    rooms["r2c1"] = create_object(
        RoomBase,
        key="Outside Piglet's House",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying about. Piglet's "
             "house is to the west. A sign by the door says 'Trespassers "
             "Will'."),
        ],
    )

    rooms["r2c2"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. Piglets house "
             "can be seen to the west and to the north you see six pine "
             "trees."),
        ],
    )

    rooms["r2c3"] = create_object(
        RoomBase,
        key="Hollow Log",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a "
             "hollow log here that you could sit on and think. This "
             "appears to be a very thoughtful spot."),
        ],
    )

    rooms["r2c4"] = create_object(
        RoomBase,
        key="Hollow Log",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a "
             "hollow log here that you could sit on and think. This "
             "appears to be a very thoughtful spot."),
        ],
    )

    rooms["r2c5"] = create_object(
        RoomBase,
        key="Outside Owl's House",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a "
             "small house up in a tree here and there are lots of bird "
             "droppings on the ground."),
        ],
    )

    # ==================================================================
    #  ROW 3
    # ==================================================================

    rooms["r3c1"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. Pooh Bears "
             "house is north and Piglets house is south."),
        ],
    )

    rooms["r3c2"] = create_object(
        RoomBase,
        key="Outside Pooh's Trap",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a pit "
             "here that looks like someone tried to cover up but did not "
             "do a very good job. It looks like you could go down into "
             "the pit."),
        ],
    )

    rooms["r3c3"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. This is about "
             "the center of the woods. The hollow log is south and you "
             "can see six pine trees to the north."),
        ],
    )

    rooms["r3c4"] = create_object(
        RoomBase,
        key="Over Gopher's Hole",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. You are standing "
             "over a small hole in the ground. A loud voice and explosions "
             "can be heard coming from the hole."),
        ],
    )

    rooms["r3c5"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. Christopher "
             "Robins house is north and Owls house is south of here."),
        ],
    )

    # ==================================================================
    #  ROW 4
    # ==================================================================

    rooms["pooh_house"] = create_object(
        RoomBase,
        key="Pooh Bear's House",
        attributes=[
            ("desc",
             "You are standing inside Pooh Bears home. The place is not "
             "too clean, but you can be sure that it is cleaned out of "
             "honey."),
        ],
    )

    rooms["r4c1"] = create_object(
        RoomBase,
        key="Outside Pooh Bear's House",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. A house has "
             "been built into a tree here. A sign over the door says "
             "'Mr. Sanders'. You get the feeling that if you sat down "
             "here you would get very thoughtful."),
        ],
    )

    rooms["r4c2"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. Poohs house is "
             "to the west. You can see six pine trees to the east and a "
             "not too well covered hole to the south."),
        ],
    )

    rooms["r4c3"] = create_object(
        RoomBase,
        key="Six Pine Trees",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There are six "
             "pine trees here."),
        ],
    )

    rooms["r4c4"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. You can hear "
             "bees buzzing to the north and Christopher Robins house is "
             "to the east. There are six pine trees to the west."),
        ],
    )

    rooms["r4c5"] = create_object(
        RoomBase,
        key="Outside Christopher Robin's House",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. The door to "
             "Christopher Robins house is to the east. There is a tree "
             "here with a rope swing on it."),
        ],
    )

    rooms["christopher_house"] = create_object(
        RoomBase,
        key="Christopher Robin's House",
        attributes=[
            ("desc",
             "You are standing inside a small model of a large house. A "
             "small boys toys are piled in one corner, and tea has been "
             "set at a small table."),
        ],
    )

    # ==================================================================
    #  ROW 5
    # ==================================================================

    rooms["r5c1"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. Poohs house is "
             "to the south and Kangas house is to the north. The woods "
             "continue to the west."),
        ],
    )

    rooms["r5c2"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a "
             "sandy area to the north."),
        ],
    )

    rooms["r5c3"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. You hear bees "
             "buzzing to the east and see Rabbits house to the north. "
             "Six pine trees are to your south."),
        ],
    )

    rooms["r5c4"] = create_object(
        RoomBase,
        key="Under Bee Tree",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a "
             "large tree here, it looks like you could climb it. The "
             "sound of bees buzzing is very loud here."),
        ],
    )

    rooms["r5c5"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. Christopher "
             "Robins house is to the south and you can see big stones and "
             "rocks to the north. You can hear bees buzzing to the west."),
        ],
    )

    # ==================================================================
    #  ROW 6
    # ==================================================================

    rooms["kanga_house"] = create_object(
        RoomBase,
        key="Kanga's House",
        attributes=[
            ("desc",
             "You are in a small neatly kept house. There is a fire "
             "burning in the fireplace. Everything is just so darn "
             "cheery!"),
        ],
    )

    rooms["r6c1"] = create_object(
        RoomBase,
        key="Outside Kanga & Roo's House",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a "
             "small house to the west with lots of toys in the yard. A "
             "large sandy pit is to the east."),
        ],
    )

    rooms["r6c2"] = create_object(
        RoomBase,
        key="Sandy Pit",
        attributes=[
            ("desc",
             "You are standing in a sandy pit. The ground is covered "
             "with fallen sand castles, trenches, and silly sand "
             "sculptures."),
        ],
    )

    rooms["r6c3"] = create_object(
        RoomBase,
        key="Outside Rabbit's House",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There is a "
             "small garden here, in fact, you are standing in it. There "
             "is also a house to the north."),
        ],
    )

    rooms["r6c4"] = create_object(
        RoomBase,
        key="100 Acre Wood",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There are big "
             "stones and rocks to the east."),
        ],
    )

    rooms["r6c5"] = create_object(
        RoomBase,
        key="Big Stones and Rocks",
        attributes=[
            ("desc",
             "You are standing inside the Hundred Acre Wood. You can hear "
             "birds chirping and little animals scurrying. There are a "
             "bunch of big stones and rocks here."),
        ],
    )

    # ==================================================================
    #  ROW 7
    # ==================================================================

    rooms["rabbit_house"] = create_object(
        RoomBase,
        key="Rabbit's House",
        attributes=[
            ("desc",
             "You are standing in a small house, or rather burrow. This "
             "place looks like a real single rabbits home."),
        ],
    )

    print(f"  Created {len(rooms)} rooms.")

    # ==================================================================
    #  EXITS
    # ==================================================================

    exit_count = 0

    # ── Row 0 → Row 1 ──
    connect_bidirectional_exit(rooms["entrance"], rooms["r1c3"], "north")
    exit_count += 2

    # ── Row 1 east-west ──
    connect_bidirectional_exit(rooms["r1c1"], rooms["r1c2"], "east")
    connect_bidirectional_exit(rooms["r1c2"], rooms["r1c3"], "east")
    connect_bidirectional_exit(rooms["r1c3"], rooms["r1c4"], "east")
    connect_bidirectional_exit(rooms["r1c4"], rooms["r1c5"], "east")
    exit_count += 8

    # ── Row 1 → Row 2 (north-south) ──
    connect_bidirectional_exit(rooms["r1c1"], rooms["r2c1"], "north")
    connect_bidirectional_exit(rooms["r1c2"], rooms["r2c2"], "north")
    connect_bidirectional_exit(rooms["r1c3"], rooms["r2c3"], "north")
    connect_bidirectional_exit(rooms["r1c4"], rooms["r2c4"], "north")
    connect_bidirectional_exit(rooms["r1c5"], rooms["r2c5"], "north")
    exit_count += 10

    # ── Row 2 east-west ──
    connect_bidirectional_exit(rooms["piglet_house"], rooms["r2c1"], "east")
    connect_bidirectional_exit(rooms["r2c1"], rooms["r2c2"], "east")
    connect_bidirectional_exit(rooms["r2c2"], rooms["r2c3"], "east")
    connect_bidirectional_exit(rooms["r2c3"], rooms["r2c4"], "east")
    connect_bidirectional_exit(rooms["r2c4"], rooms["r2c5"], "east")
    exit_count += 10

    # ── Row 2 → Row 3 (north-south) ──
    connect_bidirectional_exit(rooms["r2c1"], rooms["r3c1"], "north")
    connect_bidirectional_exit(rooms["r2c2"], rooms["r3c2"], "north")
    connect_bidirectional_exit(rooms["r2c3"], rooms["r3c3"], "north")
    connect_bidirectional_exit(rooms["r2c4"], rooms["r3c4"], "north")
    connect_bidirectional_exit(rooms["r2c5"], rooms["r3c5"], "north")
    exit_count += 10

    # ── Row 3 east-west ──
    connect_bidirectional_exit(rooms["r3c1"], rooms["r3c2"], "east")
    connect_bidirectional_exit(rooms["r3c2"], rooms["r3c3"], "east")
    connect_bidirectional_exit(rooms["r3c3"], rooms["r3c4"], "east")
    connect_bidirectional_exit(rooms["r3c4"], rooms["r3c5"], "east")
    exit_count += 8

    # ── Row 3 → Row 4 (north-south) ──
    connect_bidirectional_exit(rooms["r3c1"], rooms["r4c1"], "north")
    connect_bidirectional_exit(rooms["r3c2"], rooms["r4c2"], "north")
    connect_bidirectional_exit(rooms["r3c3"], rooms["r4c3"], "north")
    connect_bidirectional_exit(rooms["r3c4"], rooms["r4c4"], "north")
    connect_bidirectional_exit(rooms["r3c5"], rooms["r4c5"], "north")
    exit_count += 10

    # ── Row 4 east-west ──
    connect_bidirectional_exit(rooms["pooh_house"], rooms["r4c1"], "east")
    connect_bidirectional_exit(rooms["r4c1"], rooms["r4c2"], "east")
    connect_bidirectional_exit(rooms["r4c2"], rooms["r4c3"], "east")
    connect_bidirectional_exit(rooms["r4c3"], rooms["r4c4"], "east")
    connect_bidirectional_exit(rooms["r4c4"], rooms["r4c5"], "east")
    connect_bidirectional_exit(rooms["r4c5"], rooms["christopher_house"], "east")
    exit_count += 12

    # ── Row 4 → Row 5 (north-south) ──
    connect_bidirectional_exit(rooms["r4c1"], rooms["r5c1"], "north")
    connect_bidirectional_exit(rooms["r4c2"], rooms["r5c2"], "north")
    connect_bidirectional_exit(rooms["r4c3"], rooms["r5c3"], "north")
    connect_bidirectional_exit(rooms["r4c4"], rooms["r5c4"], "north")
    connect_bidirectional_exit(rooms["r4c5"], rooms["r5c5"], "north")
    exit_count += 10

    # ── Row 5 east-west ──
    connect_bidirectional_exit(rooms["r5c1"], rooms["r5c2"], "east")
    connect_bidirectional_exit(rooms["r5c2"], rooms["r5c3"], "east")
    connect_bidirectional_exit(rooms["r5c3"], rooms["r5c4"], "east")
    connect_bidirectional_exit(rooms["r5c4"], rooms["r5c5"], "east")
    exit_count += 8

    # ── Row 5 → Row 6 (north-south) ──
    connect_bidirectional_exit(rooms["r5c1"], rooms["r6c1"], "north")
    connect_bidirectional_exit(rooms["r5c2"], rooms["r6c2"], "north")
    connect_bidirectional_exit(rooms["r5c3"], rooms["r6c3"], "north")
    connect_bidirectional_exit(rooms["r5c4"], rooms["r6c4"], "north")
    connect_bidirectional_exit(rooms["r5c5"], rooms["r6c5"], "north")
    exit_count += 10

    # ── Row 6 east-west ──
    connect_bidirectional_exit(rooms["kanga_house"], rooms["r6c1"], "east")
    connect_bidirectional_exit(rooms["r6c1"], rooms["r6c2"], "east")
    connect_bidirectional_exit(rooms["r6c2"], rooms["r6c3"], "east")
    connect_bidirectional_exit(rooms["r6c3"], rooms["r6c4"], "east")
    connect_bidirectional_exit(rooms["r6c4"], rooms["r6c5"], "east")
    exit_count += 10

    # ── Row 6 → Row 7 ──
    connect_bidirectional_exit(rooms["r6c3"], rooms["rabbit_house"], "north")
    exit_count += 2

    # ── Vertical exits (Owl's House up from r2c5) ──
    # Owl's house, Pooh's Trap pit, Gopher's Hole — to be added later

    print(f"  Created {exit_count} exits.")

    # ==================================================================
    #  TAGS
    # ==================================================================

    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # ── Terrain ──
    # Outdoor forest rooms
    outdoor = [r for k, r in rooms.items() if k not in (
        "piglet_house", "pooh_house", "kanga_house",
        "rabbit_house", "christopher_house",
    )]
    for room in outdoor:
        room.set_terrain(TerrainType.FOREST.value)
        room.max_height = 1

    # Indoor rooms (houses)
    indoor = [
        rooms["piglet_house"], rooms["pooh_house"], rooms["kanga_house"],
        rooms["rabbit_house"], rooms["christopher_house"],
    ]
    for room in indoor:
        room.set_terrain(TerrainType.UNDERGROUND.value)
        room.max_height = 0
        room.always_lit = True

    print("  Tagged all rooms (zone, district, terrain).")

    # ==================================================================
    #  LIBRARY BOOK
    # ==================================================================

    # Find the library children's section
    from evennia.objects.models import ObjectDB
    library_children = ObjectDB.objects.filter(
        db_key="Children's Section",
        db_tags__db_key=DISTRICT,
    ).first()
    if not library_children:
        # Fallback: search by key in millholm_town district
        library_children = ObjectDB.objects.filter(
            db_key="Children's Section",
        ).first()

    if library_children:
        book = create_object(
            "typeclasses.world_objects.library_book.LibraryBook",
            key="The Adventures of Winnie the Pooh",
            location=library_children,
        )
        book.book_description = (
            "You open the worn, honey-stained cover and begin to read. "
            "The words blur and swirl before your eyes, and the smell of "
            "the library fades, replaced by warm summer air, the buzzing "
            "of bees, and the gentle rustling of leaves. The world around "
            "you dissolves into dappled sunlight and soft green woods..."
        )
        book.book_destination = rooms["entrance"]
        book.tags.add(ZONE, category="zone")
        print(f"  Placed 'The Adventures of Winnie the Pooh' in {library_children.key}")
    else:
        print("  [!] Children's Section not found — skipping book placement")

    print("\n=== HUNDRED ACRE WOOD BUILD COMPLETE ===\n")

    return {"entry": rooms["entrance"]}


def soft_deploy():
    """Wipe and rebuild the Hundred Acre Wood."""
    clean_hundred_acre_wood()
    build_hundred_acre_wood()

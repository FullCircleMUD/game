"""
Castle wall test area — demonstrates height adapter Pattern 1
(same destination, different arrival height).

Two rooms south of Limbo:
  Outside Castle Wall (max_height=2)
    → south at height 1: fly onto wall top, land (arrival 0)
    → south at height 2: fly over wall, stay airborne (arrival 1)
    → ground level: no south exit visible

  Wall Top (max_height=1)
    → north at height 0: step off wall → arrive at height 1 outside
      (fall warning, fall damage without FLY)
    → north at height 1: fly north → arrive at height 2 outside

Usage:
    @py from world.test_world.test_area_castle_wall import test_area_castle_wall; test_area_castle_wall()
"""

from evennia import create_object, ObjectDB

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.terrain.rooms.room_base import RoomBase


def test_area_castle_wall():
    """Build the castle wall height adapter test area south of Limbo."""

    limbo = ObjectDB.objects.get(id=2)

    # Check if already built
    existing = ObjectDB.objects.filter(db_key="Outside Castle Wall")
    if existing.exists():
        print("  Castle wall area already exists — skipping.")
        return

    # ── Rooms ──────────────────────────────────────────────────────

    outside_wall = create_object(
        RoomBase,
        key="Outside Castle Wall",
        attributes=[
            ("max_height", 2),
            ("max_depth", 0),
            ("desc",
             "A massive stone wall rises to the south, its battlements "
             "silhouetted against the sky. The wall is far too high to "
             "climb, but a skilled flier might be able to reach the top "
             "— or clear it entirely."),
        ],
    )
    outside_wall.vert_descriptions = {
        0: (
            "A massive stone wall rises to the south, its battlements "
            "silhouetted against the sky. The wall is far too high to "
            "climb, but a skilled flier might be able to reach the top "
            "— or clear it entirely."
        ),
        1: (
            "You hover at the height of the castle wall. The battlements "
            "are just ahead — you could land on the wall top to the south, "
            "or fly higher to clear it."
        ),
        2: (
            "From up here you can see over the castle wall entirely. "
            "The wall top stretches below you to the south, and beyond "
            "it a courtyard is visible."
        ),
    }
    outside_wall.always_lit = True

    wall_top = create_object(
        RoomBase,
        key="Wall Top",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc",
             "You stand on the broad stone battlements of the castle wall. "
             "The ground is a dizzying distance below on both sides. Wind "
             "whips at your clothes. To the north, the land stretches out "
             "far below."),
        ],
    )
    wall_top.vert_descriptions = {
        0: (
            "You stand on the broad stone battlements of the castle wall. "
            "The ground is a dizzying distance below on both sides. Wind "
            "whips at your clothes. To the north, the land stretches out "
            "far below."
        ),
        1: (
            "You hover above the castle wall. The battlements are just "
            "below your feet, and the ground far below on either side."
        ),
    }
    wall_top.always_lit = True

    # ── Exits ──────────────────────────────────────────────────────

    # Limbo → Outside Castle Wall
    exit_limbo_south = create_object(
        ExitVerticalAware,
        key="Outside Castle Wall",
        location=limbo,
        destination=outside_wall,
    )
    exit_limbo_south.set_direction("south")

    # Outside Castle Wall → Limbo (return)
    exit_wall_north_to_limbo = create_object(
        ExitVerticalAware,
        key="Limbo",
        location=outside_wall,
        destination=limbo,
    )
    exit_wall_north_to_limbo.set_direction("north")

    # Outside Castle Wall → Wall Top (height-gated, Pattern 1)
    # Height 1: fly onto wall, land (arrival 0)
    # Height 2: fly over wall, stay airborne (arrival 1)
    # Ground level (0): not in dict, cannot use exit
    exit_to_wall = create_object(
        ExitVerticalAware,
        key="castle wall",
        location=outside_wall,
        destination=wall_top,
    )
    exit_to_wall.set_direction("south")
    exit_to_wall.arrival_heights = {1: 0, 2: 1}

    # Wall Top → Outside Castle Wall (height-adapted)
    # Height 0: step off wall → arrive at height 1 outside (FALL!)
    # Height 1: fly north → arrive at height 2 outside
    exit_off_wall = create_object(
        ExitVerticalAware,
        key="Outside Castle Wall",
        location=wall_top,
        destination=outside_wall,
    )
    exit_off_wall.set_direction("north")
    exit_off_wall.arrival_heights = {0: 1, 1: 2}
    exit_off_wall.fall_warning = (
        "|rYou are about to step off the castle wall. "
        "The ground is a long way down. This will hurt.|n"
    )

    print("\n=== Castle Wall Test Area Created ===")
    print("  Outside Castle Wall — south of Limbo (max_height=2)")
    print("  Wall Top — south of Outside Castle Wall")
    print()
    print("  At ground level outside: no south exit visible (can't reach wall)")
    print("  fly up → south: land on wall top (arrival height 0)")
    print("  fly up; fly up → south: fly OVER the wall (arrival height 1)")
    print()
    print("  On wall top: north steps off the wall (fall warning + damage)")
    print("  fly up on wall → north: fly over safely (arrival height 2)")
    print()

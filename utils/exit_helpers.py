"""
Exit builder helpers — create bidirectional exits in a single call.

Usage:
    from utils.exit_helpers import connect, connect_door

    # Plain bidirectional exits
    connect(room_a, room_b, "east")

    # Door pair with state descriptions
    connect_door(room_a, room_b, "south", key="an oak door",
                 closed_ab="A stout oak door blocks your way.",
                 open_ab="Through the open door you see a bakehouse.")
"""

from evennia import create_object

# Opposite direction mapping — also used by ExitDoor for reverse
# direction announcements, so keep this module-level.
OPPOSITES = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "southwest": "northeast",
    "northwest": "southeast",
    "southeast": "northwest",
    "up": "down",
    "down": "up",
    "in": "out",
    "out": "in",
}


def connect(room_a, room_b, direction, desc_ab=None, desc_ba=None):
    """
    Create bidirectional ExitVerticalAware exits between two rooms.

    Args:
        room_a: Source room.
        room_b: Destination room.
        direction: Direction from A to B (e.g. "east"). Reverse auto-derived.
        desc_ab: Exit description A to B (defaults to room_b.key).
        desc_ba: Exit description B to A (defaults to room_a.key).

    Returns:
        (exit_ab, exit_ba): The two exit objects.
    """
    from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware

    reverse = OPPOSITES[direction]

    exit_ab = create_object(
        ExitVerticalAware,
        key=desc_ab or room_b.key,
        location=room_a,
        destination=room_b,
    )
    exit_ab.set_direction(direction)

    exit_ba = create_object(
        ExitVerticalAware,
        key=desc_ba or room_a.key,
        location=room_b,
        destination=room_a,
    )
    exit_ba.set_direction(reverse)

    return exit_ab, exit_ba


def connect_door(
    room_a,
    room_b,
    direction,
    key="a heavy door",
    closed_ab=None,
    open_ab=None,
    closed_ba=None,
    open_ba=None,
    door_name="door",
    is_locked=False,
    lock_dc=15,
    key_tag=None,
    relock_seconds=0,
):
    """
    Create bidirectional ExitDoor exits between two rooms, linked as a pair.

    Args:
        room_a, room_b: The two rooms.
        direction: Direction from A to B.
        key: The door's key/name (same both sides by default).
        closed_ab/open_ab: State descriptions for A to B side.
        closed_ba/open_ba: State descriptions for B to A side.
        door_name: Findable name ("door", "gate", etc.).
        is_locked: Start locked.
        lock_dc: Difficulty class for lockpicking.
        key_tag: Key item tag for unlocking.
        relock_seconds: Auto-relock timer (0 = disabled).

    Returns:
        (door_ab, door_ba): The two linked door objects.
    """
    from typeclasses.terrain.exits.exit_door import ExitDoor

    reverse = OPPOSITES[direction]

    door_ab = create_object(ExitDoor, key=key, location=room_a, destination=room_b)
    door_ab.set_direction(direction)
    door_ab.door_name = door_name
    if closed_ab:
        door_ab.closed_desc = closed_ab
    if open_ab:
        door_ab.open_desc = open_ab
    if is_locked:
        door_ab.is_locked = is_locked
    door_ab.lock_dc = lock_dc
    if key_tag:
        door_ab.key_tag = key_tag
    door_ab.relock_seconds = relock_seconds

    door_ba = create_object(ExitDoor, key=key, location=room_b, destination=room_a)
    door_ba.set_direction(reverse)
    door_ba.door_name = door_name
    if closed_ba:
        door_ba.closed_desc = closed_ba
    if open_ba:
        door_ba.open_desc = open_ba
    if is_locked:
        door_ba.is_locked = is_locked
    door_ba.lock_dc = lock_dc
    if key_tag:
        door_ba.key_tag = key_tag
    door_ba.relock_seconds = relock_seconds

    ExitDoor.link_door_pair(door_ab, door_ba)
    return door_ab, door_ba

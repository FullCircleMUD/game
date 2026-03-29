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


def connect_trapped_door(
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
    trap_find_dc=15,
    trap_disarm_dc=15,
    trap_damage_dice="1d6",
    trap_damage_type="piercing",
    trap_description="a trap",
    trap_one_shot=True,
    trap_side="ab",
):
    """
    Create bidirectional door exits with a trap on one side.

    Same as connect_door but uses TrapDoor for the trapped side.
    The trap triggers when the door is opened from the trapped side.

    Args:
        room_a, room_b, direction, key, closed_ab/ba, open_ab/ba,
            door_name, is_locked, lock_dc, key_tag, relock_seconds:
            Same as connect_door.
        trap_find_dc: DC to detect the trap via search.
        trap_disarm_dc: DC to disarm the trap.
        trap_damage_dice: Damage on trigger (e.g. "1d6").
        trap_damage_type: Damage type (e.g. "piercing").
        trap_description: What the trap looks like when detected.
        trap_one_shot: If True, trap disarms after triggering once.
        trap_side: Which side is trapped — "ab" (A→B) or "ba" (B→A).

    Returns:
        (door_ab, door_ba): The two linked door objects.
    """
    from typeclasses.terrain.exits.exit_door import ExitDoor
    from typeclasses.terrain.exits.exit_trap_door import TrapDoor

    reverse = OPPOSITES[direction]

    TrapClass = TrapDoor if trap_side == "ab" else ExitDoor
    SafeClass = ExitDoor if trap_side == "ab" else TrapDoor

    door_ab = create_object(TrapClass, key=key, location=room_a, destination=room_b)
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

    door_ba = create_object(SafeClass, key=key, location=room_b, destination=room_a)
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

    # Configure the trap on the trapped side
    trapped_door = door_ab if trap_side == "ab" else door_ba
    trapped_door.is_trapped = True
    trapped_door.trap_armed = True
    trapped_door.trap_find_dc = trap_find_dc
    trapped_door.trap_disarm_dc = trap_disarm_dc
    trapped_door.trap_damage_dice = trap_damage_dice
    trapped_door.trap_damage_type = trap_damage_type
    trapped_door.trap_description = trap_description
    trapped_door.trap_one_shot = trap_one_shot

    return door_ab, door_ba

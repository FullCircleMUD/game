"""
Exit builder helpers — standardised exit creation for zone builders.

Every exit in the game should be created through one of these helpers.
The naming convention makes directionality and exit type explicit:

    connect_bidirectional_*    — creates exits in BOTH directions (A→B and B→A)
    connect_oneway_*           — creates a single exit in ONE direction only

Usage:
    from utils.exit_helpers import (
        connect_bidirectional_exit,
        connect_bidirectional_door_exit,
        connect_bidirectional_tripwire_exit,
        connect_oneway_loopback_exit,
    )

    connect_bidirectional_exit(room_a, room_b, "east")
    connect_bidirectional_door_exit(room_a, room_b, "south", key="an oak door")
    connect_oneway_loopback_exit(room, "west", key="Dense Forest")
"""

from evennia import create_object

from enums.size import Size

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


# ================================================================== #
#  Bidirectional Exits
# ================================================================== #


def connect_bidirectional_exit(room_a, room_b, direction, desc_ab=None, desc_ba=None,
                               max_size=Size.GARGANTUAN.value):
    """
    Create exits in BOTH directions between two rooms (A→B and B→A).

    Args:
        room_a: Source room.
        room_b: Destination room.
        direction: Direction from A to B (e.g. "east"). Reverse auto-derived.
        desc_ab: Exit description A to B (defaults to room_b.key).
        desc_ba: Exit description B to A (defaults to room_a.key).
        max_size: Largest actor size that can pass (Size.X.value).
            Defaults to gargantuan (unrestricted).

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
    exit_ab.max_size = max_size

    exit_ba = create_object(
        ExitVerticalAware,
        key=desc_ba or room_a.key,
        location=room_b,
        destination=room_a,
    )
    exit_ba.set_direction(reverse)
    exit_ba.max_size = max_size

    return exit_ab, exit_ba


# Backward-compatible aliases — will be removed in a future cleanup.
connect = connect_bidirectional_exit


def connect_bidirectional_door_exit(
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
    auto_close_seconds=300,
    max_size=Size.MEDIUM.value,
):
    """
    Create door exits in BOTH directions between two rooms, linked as a pair.

    The doors are bidirectional — opening/closing/locking one side affects
    the other via link_door_pair().

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
        auto_close_seconds: Auto-close timer (default 300 = 5 min, 0 = disabled).

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
    door_ab.auto_close_seconds = auto_close_seconds
    door_ab.max_size = max_size

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
    door_ba.auto_close_seconds = auto_close_seconds
    door_ba.max_size = max_size

    ExitDoor.link_door_pair(door_ab, door_ba)
    return door_ab, door_ba


# Backward-compatible alias.
connect_door = connect_bidirectional_door_exit


def connect_bidirectional_trapped_door_exit(
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
    auto_close_seconds=300,
    trap_find_dc=15,
    trap_disarm_dc=15,
    trap_damage_dice="1d6",
    trap_damage_type="piercing",
    trap_description="a trap",
    trap_one_shot=True,
    trap_reset_seconds=0,
    trap_effect_key=None,
    trap_effect_duration=None,
    trap_effect_duration_type=None,
    trap_side="ab",
    max_size=Size.MEDIUM.value,
):
    """
    Create door exits in BOTH directions with a trap on ONE side.

    The exits are bidirectional (you can walk A→B and B→A). The trap is
    directional — it only triggers when the door is opened from the
    trapped side. Someone opening from the other side is safe.

    Uses TrapDoor for the trapped side, ExitDoor for the safe side.

    Args:
        room_a, room_b, direction, key, closed_ab/ba, open_ab/ba,
            door_name, is_locked, lock_dc, key_tag, relock_seconds:
            Same as connect_bidirectional_door_exit.
        trap_find_dc: DC to detect the trap via search.
        trap_disarm_dc: DC to disarm the trap.
        trap_damage_dice: Damage on trigger (e.g. "1d6").
        trap_damage_type: Damage type (e.g. "piercing").
        trap_description: What the trap looks like when detected.
        trap_one_shot: If True, trap disarms after triggering once.
        trap_reset_seconds: Auto-reset timer (0 = no reset).
        trap_effect_key: Named effect to apply on trigger (e.g. "poisoned").
        trap_effect_duration: Duration for the named effect.
        trap_effect_duration_type: Duration type ("combat_rounds" or "seconds").
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
    door_ab.auto_close_seconds = auto_close_seconds
    door_ab.max_size = max_size

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
    door_ba.auto_close_seconds = auto_close_seconds
    door_ba.max_size = max_size

    ExitDoor.link_door_pair(door_ab, door_ba)

    # Configure the trap on the trapped side only
    trapped_door = door_ab if trap_side == "ab" else door_ba
    trapped_door.is_trapped = True
    trapped_door.trap_armed = True
    trapped_door.trap_find_dc = trap_find_dc
    trapped_door.trap_disarm_dc = trap_disarm_dc
    trapped_door.trap_damage_dice = trap_damage_dice
    trapped_door.trap_damage_type = trap_damage_type
    trapped_door.trap_description = trap_description
    trapped_door.trap_one_shot = trap_one_shot
    trapped_door.trap_reset_seconds = trap_reset_seconds
    if trap_effect_key:
        trapped_door.trap_effect_key = trap_effect_key
    if trap_effect_duration is not None:
        trapped_door.trap_effect_duration = trap_effect_duration
    if trap_effect_duration_type:
        trapped_door.trap_effect_duration_type = trap_effect_duration_type

    return door_ab, door_ba


# Backward-compatible alias.
connect_trapped_door = connect_bidirectional_trapped_door_exit


def connect_bidirectional_tripwire_exit(
    room_a,
    room_b,
    direction,
    key=None,
    trap_find_dc=15,
    trap_disarm_dc=15,
    trap_damage_dice="1d6",
    trap_damage_type="piercing",
    trap_description="a thin wire stretched across the passage",
    trap_one_shot=True,
    trap_reset_seconds=0,
    trap_effect_key=None,
    trap_effect_duration=None,
    trap_effect_duration_type=None,
    trap_side="ab",
    max_size=Size.GARGANTUAN.value,
):
    """
    Create exits in BOTH directions with a tripwire trap on ONE side.

    The exits are bidirectional (you can walk A→B and B→A). The tripwire
    is directional — it only triggers when traversing from the trapped
    side. Someone walking from the other direction steps over it safely.

    The trapped side uses TripwireExit, the safe side uses ExitVerticalAware.

    Args:
        room_a: Source room.
        room_b: Destination room.
        direction: Direction from A to B. Reverse auto-derived.
        key: Exit display name (defaults to destination room's key).
        trap_find_dc: DC to detect the tripwire via search.
        trap_disarm_dc: DC to disarm the tripwire.
        trap_damage_dice: Damage on trigger (e.g. "1d6").
        trap_damage_type: Damage type (e.g. "piercing").
        trap_description: What the tripwire looks like when detected.
        trap_one_shot: If True, trap disarms after triggering once.
        trap_reset_seconds: Auto-reset timer (0 = no reset).
        trap_effect_key: Named effect to apply on trigger (e.g. "poisoned").
        trap_effect_duration: Duration for the named effect.
        trap_effect_duration_type: Duration type ("combat_rounds" or "seconds").
        trap_side: Which direction is trapped — "ab" (A→B) or "ba" (B→A).

    Returns:
        (exit_ab, exit_ba): The two exit objects.
    """
    from typeclasses.terrain.exits.exit_tripwire import TripwireExit
    from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware

    reverse = OPPOSITES[direction]

    TrapClass = TripwireExit if trap_side == "ab" else ExitVerticalAware
    SafeClass = ExitVerticalAware if trap_side == "ab" else TripwireExit

    exit_ab = create_object(
        TrapClass,
        key=key or room_b.key,
        location=room_a,
        destination=room_b,
    )
    exit_ab.set_direction(direction)
    exit_ab.max_size = max_size

    exit_ba = create_object(
        SafeClass,
        key=key or room_a.key,
        location=room_b,
        destination=room_a,
    )
    exit_ba.set_direction(reverse)
    exit_ba.max_size = max_size

    # Configure the trap on the trapped side only
    trapped_exit = exit_ab if trap_side == "ab" else exit_ba
    trapped_exit.is_trapped = True
    trapped_exit.trap_armed = True
    trapped_exit.trap_find_dc = trap_find_dc
    trapped_exit.trap_disarm_dc = trap_disarm_dc
    trapped_exit.trap_damage_dice = trap_damage_dice
    trapped_exit.trap_damage_type = trap_damage_type
    trapped_exit.trap_description = trap_description
    trapped_exit.trap_one_shot = trap_one_shot
    trapped_exit.trap_reset_seconds = trap_reset_seconds
    if trap_effect_key:
        trapped_exit.trap_effect_key = trap_effect_key
    if trap_effect_duration is not None:
        trapped_exit.trap_effect_duration = trap_effect_duration
    if trap_effect_duration_type:
        trapped_exit.trap_effect_duration_type = trap_effect_duration_type

    return exit_ab, exit_ba


# ================================================================== #
#  One-Way Exits
# ================================================================== #


def connect_oneway_loopback_exit(room, direction, key=None, destination=None,
                                 max_size=Size.GARGANTUAN.value):
    """
    Create a single exit that loops back to the same room or another room.

    Used for forest edges, deep water boundaries, lake shores — anywhere
    the player should feel like the space continues but mechanically
    redirects them. ONE-WAY — only creates one exit, no return.

    Args:
        room: The room the exit is placed in.
        direction: Direction the exit faces (e.g. "west").
        key: Exit display name (defaults to destination room's key).
        destination: Where the exit leads (defaults to room itself).
        max_size: Largest actor size that can pass (Size.X.value).
            Defaults to gargantuan (unrestricted).

    Returns:
        The exit object.
    """
    from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware

    dest = destination or room
    exit_obj = create_object(
        ExitVerticalAware,
        key=key or dest.key,
        location=room,
        destination=dest,
    )
    exit_obj.set_direction(direction)
    exit_obj.max_size = max_size
    return exit_obj


# Backward-compatible aliases.
connect_loopback_exit = connect_oneway_loopback_exit

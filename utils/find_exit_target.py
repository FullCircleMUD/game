"""
Shared helper for finding closeable/lockable targets in a room.

Used by: cmd_open, cmd_close, cmd_lock, cmd_unlock, cmd_picklock.

Supports directional qualifiers: "door south", "door s", "south door",
"gate east", "e gate", etc.
"""

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware

# Build reverse map: abbreviation → canonical direction
# e.g. {"n": "north", "north": "north", "s": "south", ...}
_ABBREV_TO_DIR = {}
for _dir, _aliases in ExitVerticalAware.DIRECTION_ALIASES.items():
    for _alias in _aliases:
        _ABBREV_TO_DIR[_alias] = _dir


def find_exit_target(caller, name):
    """
    Search room contents and exits for a target by name.

    Checks room objects first (via caller.search), then exits by
    substring match on key or exact match on aliases. If that fails,
    tries splitting a directional qualifier (e.g. "door south" or
    "south door") and matching exit by direction + remaining name.

    Args:
        caller: The character searching.
        name: The name/alias to search for.

    Returns:
        The found object, or None (with error message sent to caller).
    """
    # Check room objects first (chests, containers, etc.)
    target = caller.search(name, location=caller.location, quiet=True)
    if target:
        if isinstance(target, list):
            target = target[0]
        return target

    # Check exits (doors, gates, etc.)
    name_lower = name.lower()
    for ex in caller.location.exits:
        if name_lower in ex.key.lower():
            return ex
        if name_lower in [a.lower() for a in ex.aliases.all()]:
            return ex

    # Try directional qualifier: "door south", "s door", "gate east", etc.
    target = _find_exit_by_direction(caller, name_lower)
    if target:
        return target

    caller.msg(f"You don't see '{name}' here.")
    return None


def _find_exit_by_direction(caller, name_lower):
    """
    Split input into a direction qualifier and object name, then find
    an exit matching both.

    Handles: "door south", "south door", "door s", "s door",
             "gate east", "e gate", etc.
    """
    words = name_lower.split()
    if len(words) < 2:
        return None

    # Try each word as a potential direction qualifier
    for i, word in enumerate(words):
        direction = _ABBREV_TO_DIR.get(word)
        if not direction:
            continue

        # Remaining words form the object name
        remaining = " ".join(words[:i] + words[i + 1:]).strip()
        if not remaining:
            continue

        # Search exits with matching direction + name/alias
        for ex in caller.location.exits:
            ex_dir = getattr(ex, "direction", None)
            if ex_dir != direction:
                continue
            if remaining in ex.key.lower():
                return ex
            if remaining in [a.lower() for a in ex.aliases.all()]:
                return ex

    return None

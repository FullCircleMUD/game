"""
Direction parser — splits player input into object name and direction.

Used by exit-interacting commands (open, close, lock, unlock, picklock,
disarm_trap) to separate directional qualifiers from object names.

Examples:
    parse_direction("door south") → ("door", "south")
    parse_direction("south door") → ("door", "south")
    parse_direction("s door")     → ("door", "south")
    parse_direction("door s")     → ("door", "south")
    parse_direction("south")      → ("", "south")
    parse_direction("s")          → ("", "south")
    parse_direction("chest")      → ("chest", None)
    parse_direction("iron gate")  → ("iron gate", None)
"""

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware

# Reverse map: abbreviation/full name → canonical direction
# e.g. {"n": "north", "north": "north", "s": "south", ...}
_ABBREV_TO_DIR = {}
for _dir, _aliases in ExitVerticalAware.DIRECTION_ALIASES.items():
    for _alias in _aliases:
        _ABBREV_TO_DIR[_alias] = _dir


def parse_direction(text):
    """Split text into (name, direction).

    Tries each word as a potential direction. If found, the remaining
    words form the object name and the direction is returned as its
    canonical form.

    Returns:
        (name, direction) — name may be empty string if the entire
        input was a direction. direction is None if no directional
        word was found.
    """
    words = text.strip().lower().split()
    if not words:
        return ("", None)

    # Single word — check if it's a direction
    if len(words) == 1:
        direction = _ABBREV_TO_DIR.get(words[0])
        if direction:
            return ("", direction)
        return (words[0], None)

    # Multi-word — try each word as a direction
    for i, word in enumerate(words):
        direction = _ABBREV_TO_DIR.get(word)
        if direction:
            remaining = " ".join(words[:i] + words[i + 1:]).strip()
            return (remaining, direction)

    # No direction found
    return (text.strip(), None)

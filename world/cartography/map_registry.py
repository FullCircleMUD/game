"""
Map Registry — central store for all predefined ASCII district maps.

Each map definition is a dict:
    {
        "key":         str,             # unique map key (e.g. "millholm_town")
        "display_name": str,            # shown in inventory (e.g. "Millholm Town")
        "template":    str,             # full ASCII string, newline-separated rows
        "point_cells": dict,            # {point_key: [(row, col), ...]}
    }

Rooms are tagged with category="map_cell" and value "<map_key>:<point_key>".
A room can carry multiple map_cell tags to appear on more than one map.

Usage:
    from world.cartography.map_registry import get_map, get_map_keys_for_room, render_map
"""

MAP_REGISTRY = {}


def register_map(map_def):
    """Register a map definition. Called from each map file."""
    MAP_REGISTRY[map_def["key"]] = map_def


def get_map(key):
    """Return the map definition for the given key, or None."""
    # Ensure all maps are loaded (import side-effects fire once)
    _ensure_maps_loaded()
    return MAP_REGISTRY.get(key)


def get_all_maps():
    """Return all registered map definitions."""
    _ensure_maps_loaded()
    return dict(MAP_REGISTRY)


def get_map_keys_for_room(room):
    """
    Return list of (map_key, point_key) tuples from the room's map_cell tags.

    A room can appear on multiple maps if it has multiple map_cell tags.
    """
    tags = room.tags.get(category="map_cell", return_list=True) or []
    result = []
    for tag in tags:
        if ":" in tag:
            map_key, point_key = tag.split(":", 1)
            result.append((map_key, point_key))
    return result


def render_map(map_def, surveyed_points):
    """
    Build the ASCII display string for a map, masking unsurveyed cells.

    Unexplored point cells are replaced with '░' before the string is sent
    to the client. Structural characters (dashes, pipes, spaces, etc.) that
    are not part of any point_cells entry are always shown. This means:
      - The client NEVER receives hidden room positions
      - Cheating via text selection is impossible

    Args:
        map_def:         The map definition dict from MAP_REGISTRY.
        surveyed_points: Set of point_key strings the holder has surveyed.

    Returns:
        ASCII string ready to send to a player.
    """
    lines = map_def["template"].split("\n")
    point_cells = map_def["point_cells"]  # {point_key: [(row, col), ...]}

    # Build a lookup: (row, col) → point_key, for all point positions
    all_point_positions = {}
    for pk, positions in point_cells.items():
        for pos in positions:
            all_point_positions[pos] = pk

    # Which positions are visible (surveyed)
    visible_positions = set()
    for pk in surveyed_points:
        positions = point_cells.get(pk, [])
        visible_positions.update(positions)

    result = []
    for row_idx, line in enumerate(lines):
        rendered = []
        for col_idx, char in enumerate(line):
            pos = (row_idx, col_idx)
            if pos in all_point_positions:
                rendered.append(char if pos in visible_positions else "░")
            else:
                rendered.append(char)  # structural — always shown
        result.append("".join(rendered))
    return "\n".join(result)


# ── Lazy loading ──────────────────────────────────────────────────────────

_maps_loaded = False


def _ensure_maps_loaded():
    """Import the maps package once so all register_map() calls fire."""
    global _maps_loaded
    if not _maps_loaded:
        _maps_loaded = True
        import world.cartography.maps  # noqa: F401

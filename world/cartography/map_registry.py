"""
Map Registry — central store for all predefined ASCII district maps.

Each map definition is a dict:
    {
        "key":         str,             # unique map key (e.g. "millholm_town")
        "display_name": str,            # shown in inventory (e.g. "Millholm Town")
        "template":    str,             # full ASCII string, newline-separated rows
        "point_cells": dict,            # {point_key: {"pos": [(row,col),...], "poi": str}}
    }

point_cells format: each value is a dict with "pos" (list of (row,col) tuples)
and "poi" (POI type string from poi_symbols.py). Legacy format {key: [(row,col),...]}
is auto-detected and treated as poi type "unknown".

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


def _get_positions_and_poi(point_cells):
    """
    Normalise point_cells to position lookups.

    Handles both new format {key: {"pos": [...], "poi": str}}
    and legacy format {key: [(row,col), ...]}.

    Returns:
        all_positions: {(row,col): point_key}
        poi_lookup:    {(row,col): poi_type_string}
    """
    all_positions = {}
    poi_lookup = {}
    for pk, cell_data in point_cells.items():
        if isinstance(cell_data, dict):
            positions = cell_data["pos"]
            poi = cell_data.get("poi", "unknown")
        else:
            # Legacy: cell_data is a list of (row, col) tuples
            positions = cell_data
            poi = "unknown"
        for pos in positions:
            all_positions[pos] = pk
            poi_lookup[pos] = poi
    return all_positions, poi_lookup


def render_map(map_def, surveyed_points):
    """
    Build the ASCII display string for a map, masking unsurveyed cells.

    Unsurveyed point cells are replaced with spaces. Structural characters
    (dashes, pipes) only render if at least one adjacent point cell is
    visible. POI symbols are looked up from the central registry at render
    time — the template characters at cell positions are ignored.

    Args:
        map_def:         The map definition dict from MAP_REGISTRY.
        surveyed_points: Set of point_key strings the holder has surveyed.

    Returns:
        (rendered_ascii, legend_string) tuple.
    """
    from world.cartography.poi_symbols import POI_SYMBOLS, POI_NAMES

    lines = map_def["template"].split("\n")
    point_cells = map_def["point_cells"]

    all_positions, poi_lookup = _get_positions_and_poi(point_cells)

    # Which positions are visible (surveyed)
    visible_positions = set()
    for pk in surveyed_points:
        cell_data = point_cells.get(pk)
        if cell_data is None:
            continue
        positions = cell_data["pos"] if isinstance(cell_data, dict) else cell_data
        visible_positions.update(positions)

    # Collect visible POI types for the legend
    visible_poi_types = set()

    result = []
    for row_idx, line in enumerate(lines):
        rendered = []
        for col_idx, char in enumerate(line):
            pos = (row_idx, col_idx)
            if pos in all_positions:
                if pos in visible_positions:
                    poi_type = poi_lookup[pos]
                    symbol = POI_SYMBOLS.get(poi_type, char)
                    rendered.append(symbol)
                    visible_poi_types.add(poi_type)
                else:
                    rendered.append(" ")
            elif char in ("-", "|"):
                # Structural: only show if an adjacent point cell is visible
                if _has_visible_neighbor(row_idx, col_idx, char,
                                        all_positions, visible_positions):
                    rendered.append(char)
                else:
                    rendered.append(" ")
            else:
                rendered.append(char)
        result.append("".join(rendered))

    rendered_ascii = "\n".join(result)

    # Build legend from visible POI types
    legend_parts = []
    for poi_type in sorted(visible_poi_types):
        sym = POI_SYMBOLS.get(poi_type, "?")
        name = POI_NAMES.get(poi_type, poi_type)
        legend_parts.append(f"{sym}={name}")
    legend = "  ".join(legend_parts) if legend_parts else ""

    return rendered_ascii, legend


def _has_visible_neighbor(row, col, char, all_positions, visible_positions):
    """
    Check if a structural character connects to at least one visible point cell.

    Walks in both directions along the structural axis (left/right for '-',
    up/down for '|') until hitting a point cell. Shows the character if at
    least one connected point cell is visible.
    """
    if char == "-":
        directions = [(0, -1), (0, 1)]
    elif char == "|":
        directions = [(-1, 0), (1, 0)]
    else:
        return True

    for dr, dc in directions:
        r, c = row + dr, col + dc
        # Walk until we hit a point cell or go out of bounds
        for _ in range(20):  # safety limit
            pos = (r, c)
            if pos in all_positions:
                if pos in visible_positions:
                    return True
                break  # hit an unsurveyed point cell — stop this direction
            r += dr
            c += dc
    return False


# ── Lazy loading ──────────────────────────────────────────────────────────

_maps_loaded = False


def _ensure_maps_loaded():
    """Import the maps package once so all register_map() calls fire."""
    global _maps_loaded
    if not _maps_loaded:
        _maps_loaded = True
        import world.cartography.maps  # noqa: F401

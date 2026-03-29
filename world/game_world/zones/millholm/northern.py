"""
Millholm Northern — the scrubland and lake north of town.

Two static rooms bookending a procedural passage:
- Lake Track: rough scrubland north of town, south end of passage
- Lake Shore: the southern shore of a freshwater lake, north end

The procedural lake_passage connects them (5 rooms of scrub/meadow).
Cross-district connection (north_road → lake_track) is created in
soft_deploy.py after both town and northern are built.

Usage:
    from world.game_world.zones.millholm.northern import build_millholm_northern
    build_millholm_northern()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from utils.exit_helpers import connect


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_northern"


def build_millholm_northern():
    """Build the Millholm Northern district and return a dict of rooms."""
    rooms = {}

    print("  Building northern district rooms...")

    rooms["lake_track"] = create_object(
        RoomBase,
        key="Lake Track",
        attributes=[
            ("desc",
             "The cobbled road out of Millholm ends here, giving way "
             "to a rough track that heads north through open scrubland. "
             "Gorse and bracken press in from either side, and the "
             "ground is soft and uneven. The town is visible to the "
             "south — chimney smoke and slate rooftops above the tree "
             "line. Northward the land opens up into rolling meadow, "
             "and there's a dampness to the air that suggests water "
             "somewhere ahead."),
            ("details", {
                "gorse": (
                    "Thick gorse bushes with wicked thorns and bright "
                    "yellow flowers. Linnets and stonechats flit between "
                    "the branches."
                ),
                "track": (
                    "More of a suggestion than a road — two faint lines "
                    "through the scrub where feet have beaten down the "
                    "grass. It heads north toward the open meadows."
                ),
            }),
        ],
    )

    rooms["lake_shore"] = create_object(
        RoomBase,
        key="Lake Shore",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "The scrubland gives way to a pebbly shore at the edge "
             "of a broad freshwater lake. The water is clear and still, "
             "reflecting the sky like a vast mirror. Reeds and bulrushes "
             "fringe the shallows, and a wooden jetty — old but solid — "
             "extends a few yards out over the water. Ducks and moorhens "
             "paddle among the lily pads. The lake stretches away to the "
             "north, its far shore lost in a blue-grey haze."),
            ("details", {
                "jetty": (
                    "A simple wooden jetty built from heavy planks "
                    "and oak posts driven into the lake bed. The wood "
                    "is grey with age but solid underfoot. A rusted "
                    "iron ring is bolted to the end — for mooring a "
                    "boat, though none is present."
                ),
                "reeds": (
                    "Tall green reeds and bulrushes crowd the shallows, "
                    "their stems rustling in the breeze. A moorhen "
                    "picks its way between them, bobbing its head."
                ),
                "water": (
                    "Clear, cold freshwater. You can see the pebbly "
                    "bottom in the shallows — smooth stones, water "
                    "weed, and the occasional darting fish. Further "
                    "out the water deepens to a dark green."
                ),
                "lake": (
                    "A broad freshwater lake, perhaps half a mile "
                    "across. The surface is calm, broken only by "
                    "the ripples of feeding fish and the wakes of "
                    "waterfowl. The far shore is a dark line of "
                    "trees."
                ),
            }),
        ],
    )

    print(f"  Created {len(rooms)} northern rooms.")

    # ══════════════════════════════════════════════════════════════════
    # TAGS — zone, district, terrain, properties
    # ══════════════════════════════════════════════════════════════════

    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.sheltered = False  # outdoor, weather-exposed

    rooms["lake_track"].set_terrain(TerrainType.PLAINS.value)
    rooms["lake_shore"].set_terrain(TerrainType.COASTAL.value)

    print("  Tagged all northern rooms (zone, district, terrain, weather).")
    print("  Millholm Northern complete.\n")

    return rooms

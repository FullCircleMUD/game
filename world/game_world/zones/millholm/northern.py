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
DISTRICT = "millholm_lake"


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

    rooms["lake_shore_west"] = create_object(
        RoomBase,
        key="Western Lake Shore",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "The western shore of the lake curves away into a sheltered "
             "cove where the water is shallow and still. Willow trees "
             "trail their branches into the lake, and the bank is soft "
             "mud dotted with the prints of deer and foxes. A heron "
             "stands motionless in the shallows, watching for fish with "
             "infinite patience. The reeds here grow thick, creating "
             "a natural screen from the rest of the shore."),
            ("details", {
                "willows": (
                    "Graceful willow trees lean out over the water, "
                    "their long trailing branches dipping into the "
                    "surface and creating curtains of green. The bark "
                    "is deeply furrowed and silver-grey."
                ),
                "heron": (
                    "A grey heron, utterly still, standing knee-deep "
                    "in the shallows. Its long neck is coiled like a "
                    "spring. It watches the water with a yellow eye, "
                    "waiting for the flicker of a fish."
                ),
                "prints": (
                    "Animal tracks pressed into the soft mud along the "
                    "waterline — the neat slots of deer hooves, the "
                    "pads of a fox, and the webbed prints of ducks."
                ),
            }),
        ],
    )

    rooms["lake_shore_east"] = create_object(
        RoomBase,
        key="Eastern Lake Shore",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "The eastern shore is rockier than the rest, with flat "
             "slabs of grey stone jutting out into the water like "
             "natural platforms. The water is deeper here — the bottom "
             "drops away sharply just a few feet from the edge. "
             "Dragonflies skim the surface, and swallows swoop low "
             "to drink on the wing. A tumble of boulders at the "
             "water's edge looks like it was once a wall or foundation "
             "of some kind, long since reclaimed by the lake."),
            ("details", {
                "stones": (
                    "Flat grey stone slabs, smooth and sun-warmed. "
                    "They make good platforms for sitting, fishing, "
                    "or diving into the deeper water beyond."
                ),
                "boulders": (
                    "A tumble of large stones at the water's edge, "
                    "too regular to be natural. The remains of a wall "
                    "or building foundation, perhaps. Whatever stood "
                    "here is long gone — only the lake remembers."
                ),
                "dragonflies": (
                    "Electric-blue dragonflies hover and dart over the "
                    "water's surface, snatching midges from the air. "
                    "Their wings catch the light like stained glass."
                ),
            }),
        ],
    )

    print(f"  Created {len(rooms)} northern rooms.")

    # ══════════════════════════════════════════════════════════════════
    # EXITS — lake shore connections
    # ══════════════════════════════════════════════════════════════════

    connect(rooms["lake_shore_west"], rooms["lake_shore"], "east")
    connect(rooms["lake_shore"], rooms["lake_shore_east"], "east")

    print("  Created 4 lake shore exits.")

    # ══════════════════════════════════════════════════════════════════
    # TAGS — zone, district, terrain, properties
    # ══════════════════════════════════════════════════════════════════

    # Lake track is town-side of the passage — tagged as town
    rooms["lake_track"].tags.add(ZONE, category="zone")
    rooms["lake_track"].tags.add("millholm_town", category="district")
    rooms["lake_track"].set_terrain(TerrainType.PLAINS.value)
    rooms["lake_track"].sheltered = False

    # Lake shore rooms are the lake district
    lake_rooms = [
        rooms["lake_shore"], rooms["lake_shore_west"],
        rooms["lake_shore_east"],
    ]
    for room in lake_rooms:
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.COASTAL.value)
        room.sheltered = False

    print("  Tagged all northern rooms (zone, district, terrain, weather).")
    print("  Millholm Lake complete.\n")

    return rooms

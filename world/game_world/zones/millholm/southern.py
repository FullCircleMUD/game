"""
Millholm Southern District — the forest, gnolls camp and Shadowsward beyond the south gate.



The district has two entrances:
- North: from town_rooms["south_gate"] (wired in build_game_world.py)
- West: from farm_rooms["south_fork_end"] (wired in build_game_world.py)

The barrow entrance is hidden (is_hidden=True, find_dc=15) — players must
search to find it. The necromancer inside is evil but pragmatic: a future
trainer for necromancy spells and a non-lethal quest target.

Ancient Builders glyphs in the catacombs connect to the same arc as the
mine's sealed door and the deep sewer passages.

Usage:
    from world.game_world.millholm_southern import build_millholm_southern
    build_millholm_southern()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.exits.procedural_dungeon_exit import ProceduralDungeonExit
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from typeclasses.terrain.rooms.room_inn import RoomInn
from typeclasses.terrain.rooms.room_stable import RoomStable
from utils.exit_helpers import (
    connect_bidirectional_exit,
    connect_bidirectional_door_exit,
    connect_oneway_loopback_exit,
)
import world.dungeons.templates.southern_woods_passage  # noqa: F401  (register template)


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_southern"


def build_millholm_southern():
    """
    Build the Millholm Southern District.

    Returns:
        dict of room key → room object. Key rooms for cross-district
        connections: 'countryside_road' (arrival from town south_gate
        and from farm south_fork_end).
    """
    rooms = {}

    # ══════════════════════════════════════════════════════════════════
    # 1. CREATE ROOMS
    # ══════════════════════════════════════════════════════════════════

    # ── Countryside (4 rooms) ────────────────────────────────────────

    rooms["countryside_road"] = create_object(
        RoomBase,
        key="South Road",
        attributes=[
            ("desc",
             "The road south of the town wall is a packed-earth track "
             "that runs between dry-stone walls and overgrown hedgerows. "
             "The fields on either side were once cultivated but have "
             "gone to seed — tall grass and wild flowers have reclaimed "
             "the furrows. The town wall is visible to the north, its "
             "guard towers just breaking the treeline. A muddy trail "
             "joins from the west, winding in from the farmlands."),
        ],
    )

    rooms["farmstead_fork"] = create_object(
        RoomBase,
        key="Farmstead Fork",
        attributes=[
            ("desc",
             "The road forks at a weathered signpost, its lettering "
             "too faded to read. The main track continues south through "
             "increasingly wild countryside. A side path leads west "
             "toward a cluster of buildings half-hidden behind a "
             "crumbling stone wall — someone is living there, judging "
             "by the thin trail of smoke rising from behind the wall. "
             "The grass along the roadside is trampled flat by feet "
             "that weren't wearing boots."),
        ],
    )

    connect_bidirectional_exit(rooms["countryside_road"], rooms["farmstead_fork"], "south")

    # ── North South Track 12 rooms ───────────────────────────────────

    rooms["forests_edge"] = create_object(
        RoomBase,
        key="The Forest's Edge",
        attributes=[
            ("desc",
             "The road ends at the treeline and a narrow game trail "
             "pushes into the woods, winding between the trunks of "
             "old oak and elm. The canopy closes overhead the moment "
             "you step beneath it, trading sunlight for green gloom. "
             "The air is cooler here, damp and thick with the smell "
             "of leaf-mould. Somewhere off among the trees, a wolf "
             "howls — answered, a moment later, by another."),
        ],
    )

    connect_bidirectional_exit(rooms["farmstead_fork"], rooms["forests_edge"], "south")

    rooms["forest_track_1"] = create_object(
        RoomBase,
        key="Game Trail",
        attributes=[
            ("desc",
             "The trail threads between old oaks, their roots humped "
             "across the path and slick with moss. Deer prints and "
             "smaller tracks churn the soft mud. The woods thicken "
             "east and west — gaps between the trees that could be "
             "paths of their own, or places the undergrowth simply "
             "hasn't finished closing."),
        ],
    )

    connect_bidirectional_exit(rooms["forests_edge"], rooms["forest_track_1"], "southeast")

    rooms["forest_track_2"] = create_object(
        RoomBase,
        key="Winding Trail",
        attributes=[
            ("desc",
             "The trail bends around a fallen giant — an ancient elm "
             "split down the middle by some long-past storm, its "
             "trunk now half-buried in ivy and pale bracket fungus. "
             "The air is still and close. Briars crowd the narrow "
             "path, tugging at cloth."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_1"], rooms["forest_track_2"], "south")

    rooms["forest_track_3"] = create_object(
        RoomBase,
        key="Deepening Woods",
        attributes=[
            ("desc",
             "The canopy closes tight overhead. What little light "
             "reaches the ground is green and shifting, dappled "
             "through countless layers of leaves. The trail is "
             "barely visible now — more a suggestion in the "
             "undergrowth than a path. Ahead, the ground begins to "
             "slope gently down."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_2"], rooms["forest_track_3"], "south")

    rooms["forest_track_4"] = create_object(
        RoomBase,
        key="Trail Descent",
        attributes=[
            ("desc",
             "The slope steepens and the woods press in on either "
             "side. Grey rocky outcrops begin to break through the "
             "soil, and the air grows cooler, carrying the smell of "
             "damp stone. Somewhere below, the trail meets a cut in "
             "the earth where the wind finds a channel."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_3"], rooms["forest_track_4"], "south")

    rooms["forest_track_5"] = create_object(
        RoomBase,
        key="Ravine Approach",
        attributes=[
            ("desc",
             "The trail bends west around a stand of slender birches "
             "and drops into a cleft in the woods. Stone walls rise "
             "ahead — a narrow ravine cut into the forest floor, its "
             "lips fringed with root and fern. There is no way east "
             "or west from here; the cliffs see to that."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_4"], rooms["forest_track_5"], "southwest")

    rooms["forest_track_6"] = create_object(
        RoomBase,
        key="The Track Narrows",
        attributes=[
            ("desc",
             "The trail descends in a series of rough switchbacks "
             "onto the ravine floor. The walls close in overhead, "
             "dark with moss and weeping groundwater. Above, the "
             "canopy is cut by a ragged strip of open sky, and the "
             "trees lean in from the lips of the cut as though "
             "trying to reach across."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_5"], rooms["forest_track_6"], "south")

    rooms["forest_track_7"] = create_object(
        RoomBase,
        key="The Ravine",
        attributes=[
            ("desc",
             "Stone walls rise on either side, close enough to "
             "touch both at once. The light is thin and grey. The "
             "trail runs the length of the ravine floor — a narrow "
             "channel between the cliffs with no way out except "
             "forward or back. A small stream trickles down one "
             "wall, pooling in a shallow cup before seeping away "
             "into the earth. The silence here is strange; the "
             "cliffs swallow sound."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_6"], rooms["forest_track_7"], "south")

    rooms["forest_track_8"] = create_object(
        RoomBase,
        key="Narrowing Track",
        attributes=[
            ("desc",
             "The trail climbs out of the cut through a second run "
             "of switchbacks. The walls fall away, the sky widens, "
             "and the woods close back in — older, here, the trees "
             "larger and the undergrowth sparser beneath their "
             "heavy canopy. The feeling of being boxed in finally "
             "eases."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_7"], rooms["forest_track_8"], "southwest")

    rooms["forest_track_9"] = create_object(
        RoomBase,
        key="Old Wood",
        attributes=[
            ("desc",
             "The trees here are old — thick-trunked and tall, "
             "their branches beginning only well above head height "
             "so the forest floor is open and walkable in every "
             "direction. The trail widens a little, though the "
             "canopy above is as dense as ever. Side gaps east and "
             "west could lead deeper into the woods."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_8"], rooms["forest_track_9"], "south")

    rooms["forest_track_10"] = create_object(
        RoomBase,
        key="Birch Stand",
        attributes=[
            ("desc",
             "The trail swings east around a dense stand of birches "
             "whose pale bark is luminous in the dim light. The "
             "undergrowth is thicker here — fern and bracken pushing "
             "in from both sides. Somewhere off among the trunks, a "
             "branch cracks under weight."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_9"], rooms["forest_track_10"], "southeast")

    rooms["forest_track_11"] = create_object(
        RoomBase,
        key="Thinning Woods",
        attributes=[
            ("desc",
             "The trail runs south through thinning woods. The "
             "trees are younger here, and the undergrowth rougher — "
             "saplings and bramble fighting for the light. The "
             "canopy opens in patches, revealing fragments of "
             "overcast sky."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_10"], rooms["forest_track_11"], "south")

    rooms["forest_track_12"] = create_object(
        RoomBase,
        key="Trail's End",
        attributes=[
            ("desc",
             "The last of the forest. The trees stand well spaced "
             "now, their branches higher still, and the ground "
             "underfoot is carpeted with pine needles and last "
             "year's leaves. The air is changing — carrying from "
             "the south a drier smell, of grass and dust and open "
             "sky."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_11"], rooms["forest_track_12"], "south")


    rooms["forest_track_13"] = create_object(
        RoomBase,
        key="Forest Edge",
        attributes=[
            ("desc",
             "The trail runs out of the woods onto the edge of open "
             "grassland. Ahead, tall grass stretches south under a "
             "wide, empty sky. The trees at your back are the last "
             "stand of the southern woods. This is the end of the "
             "trail — what lies beyond will be wilder country still."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_12"], rooms["forest_track_13"], "south")


    print(f"  Created {len(rooms)} rooms.")

  
# ──Forest North East (20 rooms) ────────────────────────────────────
#
# Three generic forest descriptions rotate through non-landmark cells
# across all four grids so the woods read as one continuous backdrop.
# Each variant uses its own display name so the room name varies without
# revealing the quadrant. Landmark rooms break up the sameness with
# distinct features.

    _FG_DENSE = (
        "Dense oaks and elms crowd together, their canopies meshed so "
        "tight the light beneath them is green and dim. Fern and bracken "
        "carpet the ground between the trunks."
    )
    _FG_THICKET = (
        "A tangle of briar and young trees fills the gaps between older "
        "trunks. The undergrowth is hard going here; every step has to "
        "be fought for."
    )
    _FG_PINES = (
        "Scattered pines rise in uneven ranks, their lower branches "
        "long since shed. The ground is carpeted with brown needles "
        "that soften every footfall to silence."
    )

    # row 1

    rooms["forest_ne_11"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[
            ("desc", _FG_DENSE),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_1"], rooms["forest_ne_11"], "east")

    rooms["forest_ne_12"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[
            ("desc", _FG_DENSE),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_11"], rooms["forest_ne_12"], "east")

    rooms["forest_ne_13"] = create_object(
        RoomBase,
        key="Mossy Boulder",
        attributes=[
            ("desc",
             "A great moss-furred boulder rises from the forest floor "
             "here — the size of a small cottage, crowned with a tangle "
             "of holly and stunted birch. Its flanks are deeply "
             "weathered, carved into cups and channels by rain, and "
             "tiny ferns grow in the crevices. The stone is cold to the "
             "touch even in summer."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_12"], rooms["forest_ne_13"], "east")

    rooms["forest_ne_14"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[
            ("desc", _FG_THICKET),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_13"], rooms["forest_ne_14"], "east")

    # row 2

    rooms["forest_ne_21"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[
            ("desc", _FG_PINES),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_2"], rooms["forest_ne_21"], "east")
    connect_bidirectional_exit(rooms["forest_ne_11"], rooms["forest_ne_21"], "south")

    rooms["forest_ne_22"] = create_object(
        RoomBase,
        key="Hollow Oak",
        attributes=[
            ("desc",
             "An ancient oak stands in the middle of a small clearing, "
             "so huge that three adults joining hands could barely "
             "encircle its trunk. A dark cavity gapes in its base — a "
             "hollow large enough for a person to crawl into. The tree "
             "is still living, its upper branches thick with new "
             "leaves, but its heart is long gone."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_21"], rooms["forest_ne_22"], "east")
    connect_bidirectional_exit(rooms["forest_ne_12"], rooms["forest_ne_22"], "south")

    rooms["forest_ne_23"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[
            ("desc", _FG_THICKET),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_22"], rooms["forest_ne_23"], "east")
    connect_bidirectional_exit(rooms["forest_ne_13"], rooms["forest_ne_23"], "south")

    rooms["forest_ne_24"] = create_object(
        RoomBase,
        key="Northeast Forest",
        attributes=[
            ("desc",
             "The woods thicken eastward — trees growing closer "
             "together and the undergrowth crowding in until the ground "
             "is barely visible beneath tangled roots and briars. "
             "Animal runs thread away into the gloom. Easy to lose "
             "your footing here. Easier still to lose your sense of "
             "direction."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_23"], rooms["forest_ne_24"], "east")
    connect_bidirectional_exit(rooms["forest_ne_14"], rooms["forest_ne_24"], "south")

    # row 3

    rooms["forest_ne_31"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[
            ("desc", _FG_PINES),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_3"], rooms["forest_ne_31"], "east")
    connect_bidirectional_exit(rooms["forest_ne_21"], rooms["forest_ne_31"], "south")

    rooms["forest_ne_32"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[
            ("desc", _FG_DENSE),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_31"], rooms["forest_ne_32"], "east")
    connect_bidirectional_exit(rooms["forest_ne_22"], rooms["forest_ne_32"], "south")


    rooms["forest_ne_33"] = create_object(
        RoomBase,
        key="Fairy Ring",
        attributes=[
            ("desc",
             "A near-perfect circle of pale, rust-red mushrooms rings "
             "a patch of short grass in the middle of the woods — a "
             "good six paces across. The caps are flecked with white, "
             "and the air above them has a faint, sweet scent. "
             "Something about the arrangement makes you reluctant to "
             "step inside the ring."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_32"], rooms["forest_ne_33"], "east")
    connect_bidirectional_exit(rooms["forest_ne_23"], rooms["forest_ne_33"], "south")

    rooms["forest_ne_34"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[
            ("desc", _FG_DENSE),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_33"], rooms["forest_ne_34"], "east")
    connect_bidirectional_exit(rooms["forest_ne_24"], rooms["forest_ne_34"], "south")

    # row 4

    rooms["forest_ne_41"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[
            ("desc", _FG_THICKET),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_4"], rooms["forest_ne_41"], "east")
    connect_bidirectional_exit(rooms["forest_ne_31"], rooms["forest_ne_41"], "south")

    rooms["forest_ne_42"] = create_object(
        RoomBase,
        key="Fallen Elm",
        attributes=[
            ("desc",
             "A massive elm has come down here, torn from the earth "
             "by some long-past storm. Its root plate rears up like a "
             "dark wall, taller than a man, and its shattered trunk "
             "lies across the forest floor in splintered lengths now "
             "overgrown with ivy and pale fungus. The shallow crater "
             "left by its roots has filled with black water."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_41"], rooms["forest_ne_42"], "east")
    connect_bidirectional_exit(rooms["forest_ne_32"], rooms["forest_ne_42"], "south")

    rooms["forest_ne_43"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[
            ("desc", _FG_PINES),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_42"], rooms["forest_ne_43"], "east")
    connect_bidirectional_exit(rooms["forest_ne_33"], rooms["forest_ne_43"], "south")

    rooms["forest_ne_44"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[
            ("desc", _FG_THICKET),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_43"], rooms["forest_ne_44"], "east")
    connect_bidirectional_exit(rooms["forest_ne_34"], rooms["forest_ne_44"], "south")

    # row 5

    rooms["forest_ne_51"] = create_object(
        RoomBase,
        key="Dry Creek",
        attributes=[
            ("desc",
             "An old stream bed winds through the woods here — a "
             "shallow channel of smooth stones and dry gravel, its "
             "banks shored by tree roots. The stream has been dry for "
             "years, but a faint dampness in the air and a few "
             "surviving ferns hint it is not dead — only sleeping, "
             "waiting for the wet season."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_5"], rooms["forest_ne_51"], "east")
    connect_bidirectional_exit(rooms["forest_ne_41"], rooms["forest_ne_51"], "south")

    rooms["forest_ne_52"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[
            ("desc", _FG_PINES),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_51"], rooms["forest_ne_52"], "east")
    connect_bidirectional_exit(rooms["forest_ne_42"], rooms["forest_ne_52"], "south")

    rooms["forest_ne_53"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[
            ("desc", _FG_DENSE),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_52"], rooms["forest_ne_53"], "east")
    connect_bidirectional_exit(rooms["forest_ne_43"], rooms["forest_ne_53"], "south")

    rooms["forest_ne_54"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[
            ("desc", _FG_DENSE),
        ],
    )

    connect_bidirectional_exit(rooms["forest_ne_53"], rooms["forest_ne_54"], "east")
    connect_bidirectional_exit(rooms["forest_ne_44"], rooms["forest_ne_54"], "south")

# ──Forest North West (20 rooms) ────────────────────────────────────

    # row 1

    rooms["forest_nw_11"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_track_1"], rooms["forest_nw_11"], "west")

    rooms["forest_nw_12"] = create_object(
        RoomBase,
        key="Bramble Tangle",
        attributes=[
            ("desc",
             "Thorns rule this patch of woodland — great arching "
             "canes of bramble and dog-rose grown up between the "
             "trees into a dense, snagging wall. Paths thread through "
             "it at knee height where foxes and badgers have worn "
             "gaps. The bramble is heavy with hard green berries "
             "that will ripen, in time, to something worth gathering."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_nw_11"], rooms["forest_nw_12"], "west")

    rooms["forest_nw_13"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_nw_12"], rooms["forest_nw_13"], "west")

    rooms["forest_nw_14"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_nw_13"], rooms["forest_nw_14"], "west")

    # row 2

    rooms["forest_nw_21"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_track_2"], rooms["forest_nw_21"], "west")
    connect_bidirectional_exit(rooms["forest_nw_11"], rooms["forest_nw_21"], "south")

    rooms["forest_nw_22"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_nw_21"], rooms["forest_nw_22"], "west")
    connect_bidirectional_exit(rooms["forest_nw_12"], rooms["forest_nw_22"], "south")

    rooms["forest_nw_23"] = create_object(
        RoomBase,
        key="Granite Outcrop",
        attributes=[
            ("desc",
             "The ground shoulders up into a bare granite outcrop, "
             "grey and pitted with lichen. Trees lean out from its "
             "edges at odd angles, their roots gripping the stone "
             "like fingers. In its lee, a low shelf of rock forms a "
             "natural overhang — enough shelter for one or two to "
             "sit out of the rain."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_nw_22"], rooms["forest_nw_23"], "west")
    connect_bidirectional_exit(rooms["forest_nw_13"], rooms["forest_nw_23"], "south")

    rooms["forest_nw_24"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_nw_23"], rooms["forest_nw_24"], "west")
    connect_bidirectional_exit(rooms["forest_nw_14"], rooms["forest_nw_24"], "south")

    # row 3

    rooms["forest_nw_31"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_track_3"], rooms["forest_nw_31"], "west")
    connect_bidirectional_exit(rooms["forest_nw_21"], rooms["forest_nw_31"], "south")

    rooms["forest_nw_32"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_nw_31"], rooms["forest_nw_32"], "west")
    connect_bidirectional_exit(rooms["forest_nw_22"], rooms["forest_nw_32"], "south")

    rooms["forest_nw_33"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_nw_32"], rooms["forest_nw_33"], "west")
    connect_bidirectional_exit(rooms["forest_nw_23"], rooms["forest_nw_33"], "south")

    rooms["forest_nw_34"] = create_object(
        RoomBase,
        key="Twisted Pine",
        attributes=[
            ("desc",
             "A single twisted pine stands apart from its kin — "
             "older, thicker, bent sideways by a wind that no longer "
             "blows. Its bark is scored with long, pale claw-marks "
             "where some large animal has sharpened itself against "
             "the trunk. The ground beneath is carpeted with cones "
             "and dry needles."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_nw_33"], rooms["forest_nw_34"], "west")
    connect_bidirectional_exit(rooms["forest_nw_24"], rooms["forest_nw_34"], "south")

    # row 4

    rooms["forest_nw_41"] = create_object(
        RoomBase,
        key="Rabbit Warren",
        attributes=[
            ("desc",
             "The ground here is riddled with burrow openings — a "
             "sprawling rabbit warren dug into the soft earth beneath "
             "a stand of young beech. Tufts of fur catch on the "
             "bramble, and the grass around the holes is cropped "
             "short by generations of nibbling. Nothing is visible "
             "at the moment, but a faint musk hangs in the air."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_4"], rooms["forest_nw_41"], "west")
    connect_bidirectional_exit(rooms["forest_nw_31"], rooms["forest_nw_41"], "south")

    rooms["forest_nw_42"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_nw_41"], rooms["forest_nw_42"], "west")
    connect_bidirectional_exit(rooms["forest_nw_32"], rooms["forest_nw_42"], "south")

    rooms["forest_nw_43"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_nw_42"], rooms["forest_nw_43"], "west")
    connect_bidirectional_exit(rooms["forest_nw_33"], rooms["forest_nw_43"], "south")

    rooms["forest_nw_44"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_nw_43"], rooms["forest_nw_44"], "west")
    connect_bidirectional_exit(rooms["forest_nw_34"], rooms["forest_nw_44"], "south")

    # row 5

    rooms["forest_nw_51"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_track_5"], rooms["forest_nw_51"], "west")
    connect_bidirectional_exit(rooms["forest_nw_41"], rooms["forest_nw_51"], "south")

    rooms["forest_nw_52"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_nw_51"], rooms["forest_nw_52"], "west")
    connect_bidirectional_exit(rooms["forest_nw_42"], rooms["forest_nw_52"], "south")

    rooms["forest_nw_53"] = create_object(
        RoomBase,
        key="Hollow Log",
        attributes=[
            ("desc",
             "A vast hollow log lies across the forest floor here, "
             "the last remains of some tree that fell an age ago. "
             "Moss has grown thick along its length, and small things "
             "live inside the hollow — a faint scrabble and rustle "
             "from the darkness at either end. A person could crouch "
             "inside and stay dry in a downpour, if they were brave "
             "about what else might already be in there."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_nw_52"], rooms["forest_nw_53"], "west")
    connect_bidirectional_exit(rooms["forest_nw_43"], rooms["forest_nw_53"], "south")

    rooms["forest_nw_54"] = create_object(
        RoomBase,
        key="Northwest Forest",
        attributes=[
            ("desc",
             "The woods thicken westward — trees growing closer "
             "together, undergrowth crowding in until the ground is "
             "barely visible beneath tangled roots and briars. Faint "
             "runs thread away into the gloom. Easy to lose your "
             "footing here, and easier still to lose your sense of "
             "direction."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_nw_53"], rooms["forest_nw_54"], "west")
    connect_bidirectional_exit(rooms["forest_nw_44"], rooms["forest_nw_54"], "south")


# ──Forest South East (20 rooms) ────────────────────────────────────

    # row 1

    rooms["forest_se_11"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_track_8"], rooms["forest_se_11"], "east")

    rooms["forest_se_12"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_se_11"], rooms["forest_se_12"], "east")

    rooms["forest_se_13"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_se_12"], rooms["forest_se_13"], "east")

    rooms["forest_se_14"] = create_object(
        RoomBase,
        key="Ant Hill",
        attributes=[
            ("desc",
             "A massive ant mound rises from the forest floor — a "
             "cone of pale, loose soil nearly waist-high, pocked "
             "with entrances and crawling with dark red wood ants. "
             "The ground around it is crusted with discarded pine "
             "needles, harvested and hauled in from every direction. "
             "Standing too close draws angry attention from the "
             "defenders."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_se_13"], rooms["forest_se_14"], "east")

    # row 2

    rooms["forest_se_21"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_track_9"], rooms["forest_se_21"], "east")
    connect_bidirectional_exit(rooms["forest_se_11"], rooms["forest_se_21"], "south")

    rooms["forest_se_22"] = create_object(
        RoomBase,
        key="Old Stump",
        attributes=[
            ("desc",
             "The stump of a truly enormous tree stands here — "
             "waist-high, some eight feet across, its top flat and "
             "weathered smooth by decades of rain. Whoever felled it "
             "did so long enough ago that young saplings have grown "
             "up around its edges. A ring of small white mushrooms "
             "follows the stump's rim like a crown."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_se_21"], rooms["forest_se_22"], "east")
    connect_bidirectional_exit(rooms["forest_se_12"], rooms["forest_se_22"], "south")

    rooms["forest_se_23"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_se_22"], rooms["forest_se_23"], "east")
    connect_bidirectional_exit(rooms["forest_se_13"], rooms["forest_se_23"], "south")

    rooms["forest_se_24"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_se_23"], rooms["forest_se_24"], "east")
    connect_bidirectional_exit(rooms["forest_se_14"], rooms["forest_se_24"], "south")

    # row 3

    rooms["forest_se_31"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_track_10"], rooms["forest_se_31"], "east")
    connect_bidirectional_exit(rooms["forest_se_21"], rooms["forest_se_31"], "south")

    rooms["forest_se_32"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_se_31"], rooms["forest_se_32"], "east")
    connect_bidirectional_exit(rooms["forest_se_22"], rooms["forest_se_32"], "south")

    rooms["forest_se_33"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_se_32"], rooms["forest_se_33"], "east")
    connect_bidirectional_exit(rooms["forest_se_23"], rooms["forest_se_33"], "south")

    rooms["forest_se_34"] = create_object(
        RoomBase,
        key="Southeast Forest",
        attributes=[
            ("desc",
             "The woods thicken eastward — trees growing closer "
             "together, undergrowth crowding in until the ground is "
             "barely visible beneath tangled roots and briars. Faint "
             "runs thread away into the gloom. Easy to lose your "
             "footing here, and easier still to lose your sense of "
             "direction."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_se_33"], rooms["forest_se_34"], "east")
    connect_bidirectional_exit(rooms["forest_se_24"], rooms["forest_se_34"], "south")

    # row 4

    rooms["forest_se_41"] = create_object(
        RoomBase,
        key="Berry Bramble",
        attributes=[
            ("desc",
             "A thicket of wild raspberry and blackcurrant fills a "
             "sunlit gap in the canopy, bushes heavy with fruit in "
             "season. Paths thread through the bramble at animal "
             "height — badger and fox runs that let the woodland "
             "folk reach the ripest berries first. The air is sweet "
             "with the faint smell of fermenting windfalls."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_11"], rooms["forest_se_41"], "east")
    connect_bidirectional_exit(rooms["forest_se_31"], rooms["forest_se_41"], "south")

    rooms["forest_se_42"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_se_41"], rooms["forest_se_42"], "east")
    connect_bidirectional_exit(rooms["forest_se_32"], rooms["forest_se_42"], "south")

    rooms["forest_se_43"] = create_object(
        RoomBase,
        key="Spider Thicket",
        attributes=[
            ("desc",
             "A stand of close-packed hazel and hawthorn is shrouded "
             "in curtains of spider-silk — great sheets and funnels "
             "spanning the gaps between branches, each with its "
             "patient architect hanging in the middle. Midges and "
             "flies trapped in the webs twitch occasionally. The "
             "spiders are none of them small."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_se_42"], rooms["forest_se_43"], "east")
    connect_bidirectional_exit(rooms["forest_se_33"], rooms["forest_se_43"], "south")

    rooms["forest_se_44"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_se_43"], rooms["forest_se_44"], "east")
    connect_bidirectional_exit(rooms["forest_se_34"], rooms["forest_se_44"], "south")

    # row 5

    rooms["forest_se_51"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_track_12"], rooms["forest_se_51"], "east")
    connect_bidirectional_exit(rooms["forest_se_41"], rooms["forest_se_51"], "south")

    rooms["forest_se_52"] = create_object(
        RoomBase,
        key="Boar Wallow",
        attributes=[
            ("desc",
             "A deep wallow has been stamped into a hollow in the "
             "forest floor — a muddy depression six paces across, "
             "the earth churned to black slurry and the surrounding "
             "bark of the nearest trees scraped raw by tusks. The "
             "smell is rich and gamy. Something heavy has been here "
             "recently, and may return."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_se_51"], rooms["forest_se_52"], "east")
    connect_bidirectional_exit(rooms["forest_se_42"], rooms["forest_se_52"], "south")

    rooms["forest_se_53"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_se_52"], rooms["forest_se_53"], "east")
    connect_bidirectional_exit(rooms["forest_se_43"], rooms["forest_se_53"], "south")

    rooms["forest_se_54"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_se_53"], rooms["forest_se_54"], "east")
    connect_bidirectional_exit(rooms["forest_se_44"], rooms["forest_se_54"], "south")


# ──Forest South West (20 rooms) ────────────────────────────────────

    # row 1

    rooms["forest_sw_11"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_track_8"], rooms["forest_sw_11"], "west")

    rooms["forest_sw_12"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_sw_11"], rooms["forest_sw_12"], "west")

    rooms["forest_sw_13"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_sw_12"], rooms["forest_sw_13"], "west")

    rooms["forest_sw_14"] = create_object(
        RoomBase,
        key="Cluster of Toadstools",
        attributes=[
            ("desc",
             "A dense cluster of enormous red-capped toadstools grows "
             "from the rotting remains of a fallen birch — caps a "
             "foot across and flecked with white spots, stems as "
             "thick as a child's arm. The air above them has a "
             "faint, sweet, slightly sickly smell. They look exactly "
             "like the sort one is warned never to eat."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_sw_13"], rooms["forest_sw_14"], "west")

    # row 2

    rooms["forest_sw_21"] = create_object(
        RoomBase,
        key="Lightning Pine",
        attributes=[
            ("desc",
             "A tall pine stands split down the middle, its trunk "
             "cloven from crown to root by a single stroke of "
             "lightning. The two halves lean apart like open doors, "
             "the exposed heartwood blackened and cracked. Despite "
             "its wound, the tree still clings to life — a few "
             "green boughs reach up from each half toward the sky."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_9"], rooms["forest_sw_21"], "west")
    connect_bidirectional_exit(rooms["forest_sw_11"], rooms["forest_sw_21"], "south")

    rooms["forest_sw_22"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_sw_21"], rooms["forest_sw_22"], "west")
    connect_bidirectional_exit(rooms["forest_sw_12"], rooms["forest_sw_22"], "south")

    rooms["forest_sw_23"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_sw_22"], rooms["forest_sw_23"], "west")
    connect_bidirectional_exit(rooms["forest_sw_13"], rooms["forest_sw_23"], "south")

    rooms["forest_sw_24"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_sw_23"], rooms["forest_sw_24"], "west")
    connect_bidirectional_exit(rooms["forest_sw_14"], rooms["forest_sw_24"], "south")

    # row 3

    rooms["forest_sw_31"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_track_10"], rooms["forest_sw_31"], "west")
    connect_bidirectional_exit(rooms["forest_sw_21"], rooms["forest_sw_31"], "south")

    rooms["forest_sw_32"] = create_object(
        RoomBase,
        key="Standing Stone",
        attributes=[
            ("desc",
             "A single standing stone rises from the forest floor — "
             "chest-high, unworked granite leaning a little to one "
             "side, its flanks furred with grey-green lichen. There "
             "is no pattern carved on it, no obvious purpose, and "
             "the surrounding trees give it a careful berth as "
             "though their roots know not to crowd."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_sw_31"], rooms["forest_sw_32"], "west")
    connect_bidirectional_exit(rooms["forest_sw_22"], rooms["forest_sw_32"], "south")

    rooms["forest_sw_33"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_sw_32"], rooms["forest_sw_33"], "west")
    connect_bidirectional_exit(rooms["forest_sw_23"], rooms["forest_sw_33"], "south")

    rooms["forest_sw_34"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_sw_33"], rooms["forest_sw_34"], "west")
    connect_bidirectional_exit(rooms["forest_sw_24"], rooms["forest_sw_34"], "south")

    # row 4

    rooms["forest_sw_41"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_track_11"], rooms["forest_sw_41"], "west")
    connect_bidirectional_exit(rooms["forest_sw_31"], rooms["forest_sw_41"], "south")

    rooms["forest_sw_42"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_sw_41"], rooms["forest_sw_42"], "west")
    connect_bidirectional_exit(rooms["forest_sw_32"], rooms["forest_sw_42"], "south")

    rooms["forest_sw_43"] = create_object(
        RoomBase,
        key="Crow's Nest Oak",
        attributes=[
            ("desc",
             "A great spreading oak holds a dark mass high in its "
             "uppermost branches — a crow's nest, or several of "
             "them, built of dry sticks over years of use. A "
             "handful of the birds are here at any time, hopping "
             "from branch to branch and barking at each other in "
             "harsh voices that carry for some distance."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_sw_42"], rooms["forest_sw_43"], "west")
    connect_bidirectional_exit(rooms["forest_sw_33"], rooms["forest_sw_43"], "south")

    rooms["forest_sw_44"] = create_object(
        RoomBase,
        key="Southwest Forest",
        attributes=[
            ("desc",
             "The woods thicken westward — trees growing closer "
             "together, undergrowth crowding in until the ground is "
             "barely visible beneath tangled roots and briars. Faint "
             "runs thread away into the gloom. Easy to lose your "
             "footing here, and easier still to lose your sense of "
             "direction."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_sw_43"], rooms["forest_sw_44"], "west")
    connect_bidirectional_exit(rooms["forest_sw_34"], rooms["forest_sw_44"], "south")

    # row 5

    rooms["forest_sw_51"] = create_object(
        RoomBase,
        key="Forest Thicket",
        attributes=[("desc", _FG_THICKET)],
    )

    connect_bidirectional_exit(rooms["forest_track_12"], rooms["forest_sw_51"], "west")
    connect_bidirectional_exit(rooms["forest_sw_41"], rooms["forest_sw_51"], "south")

    rooms["forest_sw_52"] = create_object(
        RoomBase,
        key="Pine Stand",
        attributes=[("desc", _FG_PINES)],
    )

    connect_bidirectional_exit(rooms["forest_sw_51"], rooms["forest_sw_52"], "west")
    connect_bidirectional_exit(rooms["forest_sw_42"], rooms["forest_sw_52"], "south")

    rooms["forest_sw_53"] = create_object(
        RoomBase,
        key="Dry Gully",
        attributes=[
            ("desc",
             "A shallow gully cuts across the forest floor here — a "
             "deep-worn channel of pale stones where rainwater "
             "gathers and runs in wet months. The banks are thick "
             "with fern and tangled tree roots, and the floor is "
             "scattered with driftwood left by past floods. Right "
             "now it is bone dry."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_sw_52"], rooms["forest_sw_53"], "west")
    connect_bidirectional_exit(rooms["forest_sw_43"], rooms["forest_sw_53"], "south")

    rooms["forest_sw_54"] = create_object(
        RoomBase,
        key="Dense Forest",
        attributes=[("desc", _FG_DENSE)],
    )

    connect_bidirectional_exit(rooms["forest_sw_53"], rooms["forest_sw_54"], "west")
    connect_bidirectional_exit(rooms["forest_sw_44"], rooms["forest_sw_54"], "south")


# ── Bobbin Goode Mini Area ────────────────────────────────────
#
# Layout (west side of the track, SW quadrant):
#
#                       I_moonpetal_2 (north arrival)
#                              |
#                        [North Trail]
#                              |
#                       [Holdfast Gate] ← [Forest Trail] ← I_forest (east)
#                              |   
#                  [Stable]-[Yard]- [Watchtower]
#                              |
#        [Barracks] -- [Common Fire] -- [Barn & Stores]
#                          /   |   \
#                  [Kitchen]   |     [Training Yard]
#                              |
#                      [Planning Tent]
#                              |
#                    [Bobbin's Quarters]
#
# (Actually Planning Tent sits directly below Common Fire, between
# Common Fire and Bobbin's Quarters. Corrected layout lives in the
# exits section below.)
#
# Tone: theatrical comedy with real hardship underneath — the camp
# performs merriness, but patched bedrolls, forgotten toys, and old
# prayer-tokens tell a quieter story. Descriptions aim to let a
# player choose how much they notice.

    # ── Arrival pockets (interfaces + approach trails) ──

    rooms["bobbin_goode_interface_room_forest"] = create_object(
        RoomBase,
        key="Woodland Pocket",
        attributes=[
            ("desc",
             "A small pocket of thinning woods where the canopy "
             "breaks overhead. West, a well-worn foot-path leads "
             "deeper through the trees, and faint on the breeze come "
             "the sounds of a camp — the crackle of a fire, a "
             "distant voice, and — improbably — someone tunefully "
             "bellowing a song. Behind you lies the forest proper."),
        ],
    )


    rooms["bobbin_goode_interface_room_moonpetal_2"] = create_object(
        RoomBase,
        key="Woodland Pocket",
        attributes=[
            ("desc",
             "A quiet hollow among the trees. A narrow trail — more "
             "foot-worn than cut — threads south through the woods, "
             "and on the air comes a drift of woodsmoke and the "
             "occasional distant laugh from that direction. Northward, "
             "the trees open again toward the silver-tinged moonpetal "
             "clearing."),
        ],
    )

    rooms["bobbin_north_trail"] = create_object(
        RoomBase,
        key="Back Trail",
        attributes=[
            ("desc",
             "A narrow back-path, widened from some older rabbit run "
             "by the slow and repeated passage of boots. Woodsmoke "
             "drifts steadily from the south now, and the occasional "
             "snatch of voice carries through the trees — someone "
             "calling for more wood, someone laughing, someone in "
             "the middle of a verse. The path is easy to follow if "
             "you know it is here."),
        ],
    )

    rooms["bobbin_forest_trail"] = create_object(
        RoomBase,
        key="Approach to the Camp",
        attributes=[
            ("desc",
             "The game trail widens as it approaches the camp. Boot "
             "prints overlay deer tracks, and cut stumps stand among "
             "the living trees where timber has been taken. From "
             "ahead comes the steady rhythm of an axe on wood, a "
             "burst of laughter, and the faint, tuneful bellow of "
             "someone singing — thoroughly off-key but deeply "
             "committed to the performance."),
        ],
    )

    # ── Outer camp (gate + yard + outer ring) ──

    rooms["bobbin_holdfast_gate"] = create_object(
        RoomBase,
        key="The Holdfast Gate",
        attributes=[
            ("desc",
             "A crumbling dry-stone wall marks the old farmstead "
             "boundary, broken down in places and patched with piled "
             "timber, cartwheels, and ragged canvas. The gate itself "
             "is a pair of salvaged shutters lashed to timber frames, "
             "propped open on worn pegs. A painted sign nailed to the "
             "gatepost reads 'Welcome, Friend' — with 'FRIEND' "
             "scratched out and 'SUCKER' scrawled beneath it in a "
             "second hand, and 'friend' re-written beneath that in a "
             "third. Beyond the gate, the old yard opens up."),
        ],
    )

    rooms["bobbin_stable"] = create_object(
        RoomStable,
        key="The Stable",
        attributes=[
            ("desc",
             "A converted outbuilding leaning against the old barn "
             "wall, roofed in mismatched shingles rescued from some "
             "other ruin. Three stalls stand empty but recently used, "
             "straw fresh and water troughs filled. Tack hangs on "
             "pegs along the wall: bridles mismatched, saddles in "
             "varied styles, a cart harness with the Goldwheat Farm "
             "brand burned into its leather. Whatever horses call "
             "this place home are clearly out at work."),
        ],
    )

    rooms["bobbin_yard"] = create_object(
        RoomBase,
        key="The Yard",
        attributes=[
            ("desc",
             "The old farmyard, churned to hard-packed earth by "
             "years of rough use. Lean-tos of patched canvas and "
             "salvaged plank line the inside of the perimeter wall, "
             "and a clothesline sags under a row of shirts drying in "
             "the smoke. Weapons rest in unguarded racks. Children's "
             "initials are scratched into the remaining plaster of "
             "the farmhouse wall — too old, by the weathering, to "
             "belong to anyone here now. A half-completed longbow "
             "lies on a bench beside a whittling knife, as though "
             "someone meant to come back to it shortly."),
        ],
    )

    rooms["bobbin_watchtower"] = create_object(
        RoomBase,
        key="The Watchtower",
        attributes=[
            ("desc",
             "A rickety watchtower of lashed poles rises above the "
             "old barn roof, barely stable enough to stand on. The "
             "platform gives a commanding view over the forest path "
             "and the approaches to the camp. A chalked tally on the "
             "main post counts something — travellers seen, perhaps, "
             "or friendly arrivals. A copper horn on a thong and a "
             "sling-pouch of river stones hang from a nail, ready to "
             "be used if trouble should show itself along the path."),
        ],
    )

    # ── Common Fire (hub) and middle ring ──

    rooms["bobbin_common_fire"] = create_object(
        RoomBase,
        key="The Common Fire",
        attributes=[
            ("desc",
             "A broad firepit ringed by blackened stones sits at the "
             "heart of the farmyard — the social heart of the camp. "
             "Logs and upturned barrels serve as seats, worn smooth "
             "from long sitting. The air holds the mingled smell of "
             "woodsmoke, rabbit stew, and old spilled ale. Weapons "
             "lean against the logs within easy reach. A child's "
             "wooden horse, its painted colours worn almost to "
             "nothing, sits forgotten on one of the stumps. Nobody "
             "has moved it."),
        ],
    )

    rooms["bobbin_barracks"] = create_object(
        RoomBase,
        key="The Barracks",
        attributes=[
            ("desc",
             "The shell of the old farmhouse, its roof half-"
             "collapsed and patched over with stretched hides and "
             "ragged tarpaulin. Bedrolls line the walls on straw "
             "pallets, each with its owner's small hoard of personal "
             "things — a carved locket on a leather thong, a feather "
             "tucked into a hatband, a prayer-token from the "
             "Millholm temple. Someone has pinned a yellowing "
             "pamphlet denouncing 'the so-called Bandit Goode' to "
             "the wall, with a crude red heart drawn around his name."),
        ],
    )

    rooms["bobbin_barn_stores"] = create_object(
        RoomBase,
        key="The Barn",
        attributes=[
            ("desc",
             "The old barn serves now as the camp's storehouse, its "
             "great doors long since taken for other uses. Stacks of "
             "sacks, barrels, and crates fill most of the space — "
             "grain from the farmsteads, bolts of cloth from a "
             "merchant's cart, tools and kitchenware and a great "
             "heap of mismatched cutlery. A makeshift ledger on a "
             "cask keeps careful track of every item in a "
             "surprisingly neat hand, each entry noting where the "
             "thing came from so it can, in theory, be returned one "
             "day."),
        ],
    )

    rooms["bobbin_kitchen"] = create_object(
        RoomInn,
        key="The Kitchen",
        attributes=[
            ("desc",
             "A lean-to built against the farmhouse shelters the "
             "camp's kitchen — a blackened cauldron on an iron "
             "tripod, a split-log table worn smooth by years of "
             "chopping, and a barrel of ale drawn down well past "
             "the halfway mark. A stew simmers over the coals, "
             "smelling richly of rabbit and garlic and something "
             "bitter and green. A wooden sign nailed to the ale "
             "barrel reads: 'Take What You Need — Pay What You Can "
             "— Bless You Either Way.'"),
            ("welcome_message",
             "\n|y--- The cook waves a ladle at you. "
             "'Sit, sit — there's stew on, and the ale's not "
             "entirely terrible today.' ---|n"),
        ],
    )

    rooms["bobbin_training_yard"] = create_object(
        RoomBase,
        key="The Training Yard",
        attributes=[
            ("desc",
             "A square of beaten earth off the common fire, set up "
             "for rough drill. Straw-stuffed practice butts hang "
             "from a cross-beam, each riddled with arrow holes old "
             "and new. Fencing posts wrapped in padded leather show "
             "the scars of many a duelling session, and the ground "
             "is scattered with spent arrows, broken practice "
             "shafts, and the occasional discarded bandage. A "
             "hand-painted placard leans against the cross-beam: "
             "'ALL WHO ENTER MUST ATTEMPT AT LEAST ONE JAUNTY "
             "POSE.'"),
        ],
    )

    # ── Inner sanctum (planning + Bobbin's quarters) ──

    rooms["bobbin_planning_tent"] = create_object(
        RoomBase,
        key="The Planning Tent",
        attributes=[
            ("desc",
             "A larger canvas tent, salvaged from some merchant's "
             "caravan and patched many times over. Inside, a cask-"
             "top table holds a hand-drawn map of Millholm and its "
             "surrounding countryside, marked with arrows, circled "
             "names, and a great many question marks in different "
             "hands. A hand-written manifesto is pinned to the "
             "canvas wall, beginning 'WE ROB ONLY THOSE WHO CAN "
             "SPARE IT, AND GIVE TO THOSE WHO CANNOT' — with a list "
             "of amendments and grumpy counter-arguments scrawled "
             "in the margins in other pens."),
        ],
    )

    rooms["bobbin_quarters"] = create_object(
        RoomBase,
        key="Bobbin's Quarters",
        attributes=[
            ("desc",
             "A smaller tent set a little apart from the rest, its "
             "interior partitioned by hung blankets into a makeshift "
             "private chamber. A cot, a writing desk made from a "
             "split barrel-top, and a battered sea-chest dominate "
             "the space. The chest is locked. A full-length mirror "
             "salvaged from some lady's dresser stands against one "
             "wall — and in front of it, hanging on a wooden stand, "
             "an extravagant pair of green-and-gold striped tights, "
             "carefully aired and pressed. A sheaf of lyric sheets "
             "lies on the desk, verses written out, crossed out, "
             "and rewritten in a surprisingly careful hand."),
        ],
    )

    # ── Internal exits ──

    # Interfaces → approach trails → gate
    connect_bidirectional_exit(rooms["bobbin_goode_interface_room_moonpetal_2"], rooms["bobbin_north_trail"], "south")
    connect_bidirectional_exit(rooms["bobbin_north_trail"], rooms["bobbin_holdfast_gate"], "south")
    connect_bidirectional_exit(rooms["bobbin_goode_interface_room_forest"], rooms["bobbin_forest_trail"], "west")
    connect_bidirectional_exit(rooms["bobbin_forest_trail"], rooms["bobbin_holdfast_gate"], "west")

    # Gate → yard
    connect_bidirectional_exit(rooms["bobbin_holdfast_gate"], rooms["bobbin_yard"], "south")
  
    # Yard ↔ watchtower & stable (adjacent)
    connect_bidirectional_exit(rooms["bobbin_yard"], rooms["bobbin_watchtower"], "east")
    connect_bidirectional_exit(rooms["bobbin_yard"], rooms["bobbin_stable"], "west")


    # Yard → common fire (south)
    connect_bidirectional_exit(rooms["bobbin_yard"], rooms["bobbin_common_fire"], "south")

    # Common fire ↔ middle ring
    connect_bidirectional_exit(rooms["bobbin_common_fire"], rooms["bobbin_barracks"], "west")
    connect_bidirectional_exit(rooms["bobbin_common_fire"], rooms["bobbin_barn_stores"], "east")
    connect_bidirectional_exit(rooms["bobbin_common_fire"], rooms["bobbin_kitchen"], "southwest")
    connect_bidirectional_exit(rooms["bobbin_common_fire"], rooms["bobbin_training_yard"], "southeast")

    # Common fire → planning tent → Bobbin's quarters (inner sanctum)
    connect_bidirectional_exit(rooms["bobbin_common_fire"], rooms["bobbin_planning_tent"], "south")
    connect_bidirectional_exit(rooms["bobbin_planning_tent"], rooms["bobbin_quarters"], "south")

# ── Moonpetal Clearing 1 Mini Area ────────────────────────────────────
#
# Layout (east side of the track):
#
#                     I_raven
#                        |
#                      E_north
#                        |
#       I_forest  ---  E_west  ---  M  ---  E_east
#                        |
#                      E_south
#
# Main clearing (M) is open ground carpeted with moonpetal, harvest
# max=10. The four edge rooms (E_*) are the woodland fringe — trees
# and saplings with thinner moonpetal patches, harvest max=3 each.
# Interface rooms are transitional antechambers between the mini area
# and the procedural passages that lead in.

    _MP_MAIN_ABUNDANT = (
        "You stand at the heart of the moonpetal clearing — an open "
        "meadow where the silver blooms grow thick and wild, knee-"
        "deep and drifting in the slightest breeze. The air is heavy "
        "with their sweet, faintly metallic scent, and bees move "
        "lazily between the flowers. There is plenty to 'gather'."
    )
    _MP_MAIN_SCARCE = (
        "The clearing is quieter now. Most of the moonpetal has been "
        "picked, and only a scattering of silver blooms dots the "
        "trampled grass. A few more remain to 'gather'."
    )
    _MP_MAIN_DEPLETED = (
        "The clearing has been picked clean. Only bare stems and "
        "flattened grass remain where the moonpetal grew. The meadow "
        "will need time to recover."
    )
    _MP_EDGE_ABUNDANT = (
        "The edge of the clearing, where the open meadow thins into "
        "woodland — saplings and the odd older tree rise between "
        "patches of moonpetal. Fewer blooms than the heart of the "
        "meadow, but enough silver petals scattered through the "
        "grass to be worth stopping to 'gather'."
    )
    _MP_EDGE_SCARCE = (
        "The edge of the clearing, sparse where the meadow gives way "
        "to trees. Only a bloom or two of moonpetal remain to "
        "'gather' here."
    )
    _MP_EDGE_DEPLETED = (
        "The edge of the clearing. The few moonpetal that grew here "
        "at the fringe have all been picked; only grass and sapling "
        "stems remain."
    )

    # No per-room "desc" attribute set — RoomHarvesting.get_display_desc
    # renders the tier-appropriate desc_abundant/scarce/depleted based
    # on resource_count and ignores any plain "desc".
    _MP_MAIN_ATTRS = [
        ("resource_id", 12),
        ("resource_count", 1),             # seeded with 1; UnifiedSpawnScript fills to max hourly
        ("resource_count_max", 10),
        ("abundance_threshold", 5),
        ("harvest_height", 0),
        ("harvest_command", "gather"),
        ("desc_abundant", _MP_MAIN_ABUNDANT),
        ("desc_scarce", _MP_MAIN_SCARCE),
        ("desc_depleted", _MP_MAIN_DEPLETED),
    ]

    _MP_EDGE_ATTRS = [
        ("resource_id", 12),
        ("resource_count", 1),             # seeded with 1; UnifiedSpawnScript fills to max hourly
        ("resource_count_max", 3),
        ("abundance_threshold", 2),
        ("harvest_height", 0),
        ("harvest_command", "gather"),
        ("desc_abundant", _MP_EDGE_ABUNDANT),
        ("desc_scarce", _MP_EDGE_SCARCE),
        ("desc_depleted", _MP_EDGE_DEPLETED),
    ]

    # Interface rooms (antechambers — clearing lies one room inward)

    rooms["moonpetal1_interface_room_forest"] = create_object(
        RoomBase,
        key="Woodland Pocket",
        attributes=[
            ("desc",
             "A small pocket in the woods where the canopy breaks a "
             "little. East, through a scattering of thinner trunks, "
             "a silvery glow catches the air — something luminous "
             "grows just beyond. Westward, the way back into the "
             "deep woods."),
        ],
    )


    rooms["moonpetal1_interface_room_raven_sage"] = create_object(
        RoomBase,
        key="Woodland Pocket",
        attributes=[
            ("desc",
             "A quiet hollow of trees. To the south the canopy "
             "breaks, and a silver glow shows through the trunks. "
             "Northward, a narrow trail threads back toward the "
             "yew-ringed clearing of the sage."),
        ],
    )

    # Main clearing (M) — full moonpetal, harvest max 10

    rooms["moonpetal1_main"] = create_object(
        RoomHarvesting,
        key="Moonpetal Clearing",
        attributes=_MP_MAIN_ATTRS,
    )

    # Edge rooms (E) — woodland fringe, harvest max 3

    rooms["moonpetal1_edge_north"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    rooms["moonpetal1_edge_south"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    rooms["moonpetal1_edge_east"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    rooms["moonpetal1_edge_west"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    # Internal exits — interfaces → edges → main

    connect_bidirectional_exit(rooms["moonpetal1_interface_room_forest"], rooms["moonpetal1_edge_west"], "east")
    connect_bidirectional_exit(rooms["moonpetal1_interface_room_raven_sage"], rooms["moonpetal1_edge_north"], "south")
    connect_bidirectional_exit(rooms["moonpetal1_edge_west"], rooms["moonpetal1_main"], "east")
    connect_bidirectional_exit(rooms["moonpetal1_main"], rooms["moonpetal1_edge_east"], "east")
    connect_bidirectional_exit(rooms["moonpetal1_edge_north"], rooms["moonpetal1_main"], "south")
    connect_bidirectional_exit(rooms["moonpetal1_main"], rooms["moonpetal1_edge_south"], "south")


# ── Moonpetal Clearing 2 Mini Area ────────────────────────────────────
#
# Layout (west side of the track):
#
#                    E_north
#                       |
#         E_west  ---   M   ---  E_east  ---  I_forest
#                       |
#                    E_south
#                       |
#                   I_bobbin
#
# Same structure as moonpetal1, rotated so interfaces face the correct
# neighbours — forest (NW grid) to the east, bobbin camp to the south.

    # Interface rooms (antechambers)

    rooms["moonpetal2_interface_room_forest"] = create_object(
        RoomBase,
        key="Woodland Pocket",
        attributes=[
            ("desc",
             "A pocket of thinning woods. West, through the trees, "
             "a silvery glow catches the air — something luminous "
             "grows just beyond. Eastward, the way back into the "
             "deep woods."),
        ],
    )


    rooms["moonpetal2_interface_room_bobbin_goode"] = create_object(
        RoomBase,
        key="Woodland Pocket",
        attributes=[
            ("desc",
             "A small hollow among the trees. North, the canopy "
             "opens and a silver glow shows through. Southward, the "
             "trees thicken and the way returns toward smoke and "
             "rough-edged human noise."),
        ],
    )

    # Main clearing (M) — full moonpetal, harvest max 10

    rooms["moonpetal2_main"] = create_object(
        RoomHarvesting,
        key="Moonpetal Clearing",
        attributes=_MP_MAIN_ATTRS,
    )

    # Edge rooms (E) — woodland fringe, harvest max 3

    rooms["moonpetal2_edge_north"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    rooms["moonpetal2_edge_south"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    rooms["moonpetal2_edge_east"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    rooms["moonpetal2_edge_west"] = create_object(
        RoomHarvesting,
        key="Edge of the Clearing",
        attributes=_MP_EDGE_ATTRS,
    )

    # Internal exits — interfaces → edges → main

    connect_bidirectional_exit(rooms["moonpetal2_interface_room_forest"], rooms["moonpetal2_edge_east"], "west")
    connect_bidirectional_exit(rooms["moonpetal2_interface_room_bobbin_goode"], rooms["moonpetal2_edge_south"], "north")
    connect_bidirectional_exit(rooms["moonpetal2_edge_east"], rooms["moonpetal2_main"], "west")
    connect_bidirectional_exit(rooms["moonpetal2_main"], rooms["moonpetal2_edge_west"], "west")
    connect_bidirectional_exit(rooms["moonpetal2_edge_south"], rooms["moonpetal2_main"], "north")
    connect_bidirectional_exit(rooms["moonpetal2_main"], rooms["moonpetal2_edge_north"], "north")



# ── Ravens cursed sage Mini Area ────────────────────────────────────
#
# Layout (east side of the track, NE quadrant):
#
#                          [Raven Tree]
#                               |
#                          [Yew Grove]
#                               |
#   I_forest ── east ── [Standing Stones] ── east ── [Hut Porch] ── east ── [Study]
#                               |                          |                   |   \
#                               |                          |                   N    S
#                            (south)                   (south)                 |    |
#                               |                          |              [Workshop][Bedchamber]
#                         I_moonpetal_1             [Herb Garden]              |
#                                                                        [Cellar] (hidden trapdoor, find DC 18)
#
# Tone: melancholic, ancient, gently unsettling. The sage predates
# Millholm. Every room carries hints of very-long-occupancy: a candle
# that has been burning a very long time, a chalk ward walked to
# near-invisibility, a niche in the cellar that once held something
# important.
#
# Ancient Builder glyph continuity: Standing Stones + Cellar share the
# interlocking-circles/angular-spirals motif found in the barrow, the
# mine's sealed door, and the deep sewers — binding the sage's
# hermitage into the wider world-mystery arc.
#
# Future curse-break questline (NOT wired yet; design notes):
#   - The empty stone niche in the Cellar once held the sage's
#     sealed soul-object
#   - When the containment "went wrong" (sage's story), the object
#     was moved/lost/taken to the Barrow
#   - Quest arc: player retrieves from Barrow → returns to Cellar
#     niche → curse breaks (or doesn't, per the twist)
#   - The Cellar's stone niche is the designated return-spot slot

    # ── Clearing edge interfaces (arrival points from procedural passages) ──

    rooms["raven_sage_interface_room_forest"] = create_object(
        RoomBase,
        key="Edge of the Clearing",
        attributes=[
            ("desc",
             "The woods give way to a small, shaded clearing ringed "
             "by ancient yew. Across the close-cropped grass, five "
             "standing stones rise in a small ring at the centre, "
             "and beyond them a low stone hut sits beneath a mossed "
             "thatch roof, a thin thread of pale smoke rising from "
             "the chimney. Ravens perch silently in the branches "
             "all around, watching. The air here feels faintly "
             "wrong — cooler than the trees, the light less sure of "
             "itself. Behind you lies the way back through the woods."),
        ],
    )


    rooms["raven_sage_interface_room_moonpetal1"] = create_object(
        RoomBase,
        key="Edge of the Clearing",
        attributes=[
            ("desc",
             "You come out of the woods at the southern edge of a "
             "yew-ringed clearing. Ahead, a ring of five standing "
             "stones rises from the cropped grass, and beyond them "
             "a low stone hut sits beneath its patched thatch. "
             "Ravens perch in silence all around, watching you "
             "arrive. Behind you, the air still carries the last "
             "whisper of moonpetal — sweet and silver — already "
             "fading beneath whatever stillness this place imposes."),
        ],
    )

    # ── Clearing features ──

    rooms["raven_standing_stones"] = create_object(
        RoomBase,
        key="The Standing Stones",
        attributes=[
            ("desc",
             "The heart of the clearing — a small ring of five "
             "standing stones, each about chest-high, worn by many "
             "centuries of rain and wind. Their weathered surfaces "
             "carry faint geometric carvings: interlocking circles, "
             "angular spirals, the same patterns found in the deep "
             "sewers and at the sealed door in the abandoned mine. "
             "The ring encloses a patch of close-cropped grass where "
             "nothing else seems willing to grow. The air within the "
             "circle is cooler than outside it, and the silence is "
             "somehow deeper."),
        ],
    )

    rooms["raven_yew_grove"] = create_object(
        RoomBase,
        key="The Yew Grove",
        attributes=[
            ("desc",
             "Ancient yews crowd together here, their black-green "
             "branches so dense the light beneath them is dim even "
             "at midday. Their trunks are immense — three or four "
             "paces around at the base — and deeply furrowed, the "
             "bark almost black. These trees were old before the "
             "farms were ploughed, before the town was founded, "
             "before the road was cut. A single weathered wooden "
             "bench sits among them, its surface polished to a "
             "softness by long use, facing out toward the standing "
             "stones."),
        ],
    )

    rooms["raven_tree"] = create_object(
        RoomBase,
        key="The Raven Tree",
        attributes=[
            ("desc",
             "A single enormous oak rises at the northern edge of "
             "the clearing, branching into dozens of heavy boughs "
             "in every direction. Ravens perch everywhere — on the "
             "branches, on stumps at the tree's base, among the "
             "tangled roots — dozens, perhaps a hundred. They are "
             "silent, and watching. The ground beneath is carpeted "
             "with shed black feathers and the small pale bones of "
             "things long since picked clean. None of the birds "
             "flinches at your approach. None of them caws. They "
             "simply watch."),
        ],
    )

    rooms["raven_herb_garden"] = create_object(
        RoomHarvesting,
        key="The Herb Garden",
        attributes=[
            ("resource_id", 22),               # siren petal
            ("resource_count", 1),             # seeded with 1; UnifiedSpawnScript fills to max hourly
            ("resource_count_max", 5),
            ("abundance_threshold", 2),
            ("harvest_height", 0),
            ("harvest_command", "gather"),
            ("desc_abundant",
             "A small patch of turned earth edged with rounded river "
             "stones, tucked against the south wall of the hut. Plants "
             "grow here in careful rows — dark-leaved henbane, pale "
             "mandrake, a cluster of silvery moonpetal, a dozen others "
             "both common and rare. At the south end of the garden, a "
             "shallow sunken bed holds a deeper soil where pink siren "
             "petals catch the light, ready to 'gather'. Each row is "
             "labelled on a little wooden tag in a precise, old-"
             "fashioned hand. A pair of iron shears rests on a flat "
             "stone at the garden's edge, as though set down only a "
             "moment ago by someone just out of sight."),
            ("desc_scarce",
             "A small patch of turned earth edged with rounded river "
             "stones, tucked against the south wall of the hut. Plants "
             "grow here in careful rows — dark-leaved henbane, pale "
             "mandrake, a cluster of silvery moonpetal, a dozen others "
             "both common and rare. The sunken siren-petal bed at the "
             "south end is mostly bare; only a pink bloom or two "
             "remain to 'gather'. The iron shears still rest on the "
             "flat stone at the garden's edge."),
            ("desc_depleted",
             "A small patch of turned earth edged with rounded river "
             "stones, tucked against the south wall of the hut. The "
             "henbane and mandrake stand undisturbed in their rows, "
             "but the sunken bed at the south end is bare turned soil "
             "— every siren petal has been picked. The roots will "
             "need time before the bed flowers again. The iron shears "
             "rest on the flat stone at the garden's edge."),
        ],
    )

    # ── The Hut ──

    rooms["raven_hut_porch"] = create_object(
        RoomBase,
        key="The Hut Porch",
        attributes=[
            ("desc",
             "The sage's hut stands before you — a low building of "
             "dry-fitted stone, its thatch patched and mossed but "
             "well-maintained. The door is pale wood, never stained "
             "or varnished, and the lintel above it is carved with "
             "the same geometric glyphs as the standing stones. A "
             "stone step, worn into a shallow cup by countless "
             "years of crossing, leads up to the threshold. The "
             "door is not locked. It never has been."),
        ],
    )

    rooms["raven_hut_study"] = create_object(
        RoomBase,
        key="The Study",
        attributes=[
            ("desc",
             "The heart of the sage's home — a single large room "
             "floored with slate flags, its walls lined with shelves "
             "of books and scrolls. A long oak table runs down the "
             "centre, covered with open volumes, loose sheets of "
             "research in a careful, cramped hand, and the stub of "
             "a tallow candle. A single raven perches on the back "
             "of the table's one chair, watching you with the same "
             "patient attention as its kin outside. A faded tapestry "
             "on the far wall shows a geometric pattern — circles "
             "within circles within circles — that the eye keeps "
             "trying to untangle and cannot."),
        ],
    )

    rooms["raven_hut_workshop"] = create_object(
        RoomBase,
        key="The Workshop",
        attributes=[
            ("desc",
             "A smaller chamber opening north off the study, fitted "
             "out as an alchemical workshop. A long worktable holds "
             "glass alembics, ceramic crucibles, and a rack of small "
             "glass bottles each neatly labelled in the same careful "
             "hand as the garden tags. Dried specimens hang from the "
             "rafters — bird skulls, knots of herbs, a bundle of "
             "feathers bound together with dark thread. On the floor, "
             "drawn in pale chalk long since faded to a ghost, is a "
             "complex geometric ward of interlocking circles. It has "
             "been walked across so many times the chalk is almost "
             "gone, but the shape of it remains visible in the grime. "
             "It is, unmistakably, the same pattern as the stones "
             "outside."),
        ],
    )

    rooms["raven_hut_bedchamber"] = create_object(
        RoomBase,
        key="The Bedchamber",
        attributes=[
            ("desc",
             "A small, austere chamber opening south off the study "
             "— the sage's sleeping quarters. A narrow cot stands "
             "against one wall, covered with a pale wool blanket, "
             "neatly folded. A wooden chest sits at the foot of the "
             "cot, its lid worn smooth. A single tallow candle burns "
             "in a holder on a small side table, casting a soft "
             "light across the room. The candle is nearly full — "
             "and yet the side of its base, where it has been "
             "gripped between the same finger and thumb countless "
             "times, is worn smooth and blackened. This candle has "
             "been burning, or being relit, for a very long time."),
        ],
    )

    rooms["raven_hut_cellar"] = create_object(
        RoomBase,
        key="The Cellar",
        attributes=[
            ("desc",
             "A natural cave hollowed out beneath the hut, its walls "
             "rising into a low vaulted roof. Every surface is "
             "carved with geometric glyphs — interlocking circles, "
             "angular spirals, whorls and lattices — more dense and "
             "more intricate here than anywhere above ground. At the "
             "centre of the cave, a stone niche has been cut into "
             "the living rock: a shallow shelf, perhaps the size of "
             "two cupped hands. The niche is empty. A faint dust "
             "lies in it, suggesting it once held something now "
             "absent a very long time. The air down here is "
             "perfectly still and very faintly hums — a vibration "
             "felt in the bones more than heard with the ears."),
        ],
    )

    # ── Internal exits ──

    # Interface arrivals into the clearing (hub is Standing Stones)
    connect_bidirectional_exit(rooms["raven_sage_interface_room_forest"], rooms["raven_standing_stones"], "east")
    connect_bidirectional_exit(rooms["raven_sage_interface_room_moonpetal1"], rooms["raven_standing_stones"], "north")

    # Clearing hub → features
    connect_bidirectional_exit(rooms["raven_standing_stones"], rooms["raven_yew_grove"], "north")
    connect_bidirectional_exit(rooms["raven_yew_grove"], rooms["raven_tree"], "north")
    connect_bidirectional_exit(rooms["raven_standing_stones"], rooms["raven_hut_porch"], "east")

    # Hut porch → herb garden (south) and hut interior (east)
    connect_bidirectional_exit(rooms["raven_hut_porch"], rooms["raven_herb_garden"], "south")
    connect_bidirectional_exit(rooms["raven_hut_porch"], rooms["raven_hut_study"], "east")

    # Study → workshop (north), bedchamber (south)
    connect_bidirectional_exit(rooms["raven_hut_study"], rooms["raven_hut_workshop"], "north")
    connect_bidirectional_exit(rooms["raven_hut_study"], rooms["raven_hut_bedchamber"], "south")

    # Study → Cellar via hidden trapdoor (find_dc 18, matches barrow)
    cellar_door_down, cellar_door_up = connect_bidirectional_door_exit(
        rooms["raven_hut_study"], rooms["raven_hut_cellar"], "down",
        key="a trapdoor",
        closed_ab=(
            "The slate flags of the floor are worn smooth. There is "
            "nothing remarkable about them."
        ),
        open_ab=(
            "An open trapdoor in the floor reveals stone steps "
            "descending into darkness."
        ),
        closed_ba=(
            "The trapdoor above is closed. Stone steps lead back up."
        ),
        open_ba=(
            "A shaft of pale light falls through the open trapdoor "
            "from the study above."
        ),
        door_name="trapdoor",
    )
    cellar_door_down.is_hidden = True
    cellar_door_down.find_dc = 15


# ── Procedural Passages (southern_woods_passage template) ──────────────
#
# Six procedural passages connect the main forest grids to the four
# mini-areas, and link sibling mini-areas on each side of the track.
# Each passage is two ProceduralDungeonExits (one at each anchor),
# producing two separate passage instances (one per travel direction).
#
# Forest → Mini-area (4 passages):
#   forest_ne_24 east   ↔ raven_sage   (NE forest → Raven Sage)
#   forest_se_34 east   ↔ moonpetal1   (SE forest → Moonpetal 1)
#   forest_nw_54 west   ↔ moonpetal2   (NW forest → Moonpetal 2)
#   forest_sw_44 west   ↔ bobbin_goode (SW forest → Bobbin Goode)
#
# Sibling pairs (2 passages):
#   raven_sage   ↔ moonpetal1      (east-side pair, N-S)
#   bobbin_goode ↔ moonpetal2      (west-side pair, N-S)

    _TEMPLATE_ID = "southern_woods_passage"

    def _wire_passage(room_a, dir_a, room_b, dir_b):
        """Create a pair of ProceduralDungeonExits connecting room_a ↔ room_b."""
        exit_a = create_object(
            ProceduralDungeonExit,
            key="the woods",
            location=room_a,
            destination=room_a,
        )
        exit_a.set_direction(dir_a)
        exit_a.dungeon_template_id = _TEMPLATE_ID
        exit_a.dungeon_destination_room_id = room_b.id

        exit_b = create_object(
            ProceduralDungeonExit,
            key="the woods",
            location=room_b,
            destination=room_b,
        )
        exit_b.set_direction(dir_b)
        exit_b.dungeon_template_id = _TEMPLATE_ID
        exit_b.dungeon_destination_room_id = room_a.id

    # Forest → Mini-area
    _wire_passage(
        rooms["forest_ne_24"], "east",
        rooms["raven_sage_interface_room_forest"], "west",
    )
    _wire_passage(
        rooms["forest_se_34"], "east",
        rooms["moonpetal1_interface_room_forest"], "west",
    )
    _wire_passage(
        rooms["forest_nw_54"], "west",
        rooms["moonpetal2_interface_room_forest"], "east",
    )
    _wire_passage(
        rooms["forest_sw_44"], "west",
        rooms["bobbin_goode_interface_room_forest"], "east",
    )

    # Sibling pairs
    _wire_passage(
        rooms["raven_sage_interface_room_moonpetal1"], "south",
        rooms["moonpetal1_interface_room_raven_sage"], "north",
    )
    _wire_passage(
        rooms["bobbin_goode_interface_room_moonpetal_2"], "north",
        rooms["moonpetal2_interface_room_bobbin_goode"], "south",
    )


# ── Forest Grid Edge Loop-backs ────────────────────────────────────
#
# Every outer-edge room of each 5x4 grid gets a one-way loop-back exit
# heading outward — the forest "turns you back" two rooms inward.
# This disguises the procedural-passage anchors: from the player's view,
# every outer edge room looks like it might have an exit, but only the
# ones wired to procedural passages actually lead somewhere.
#
# Col 1 of each grid is the track-facing side (already connected).
# Outward direction is east for NE/SE grids, west for NW/SW grids.
# Loop-back target is 2 rooms inward, matching the east-of-town pattern.

    def _wire_grid_loopbacks(prefix, outward_dir, anchor_row):
        """Wire outer-edge loop-backs for a 5x4 grid.

        Args:
            prefix:      e.g. 'forest_ne_' → rooms 'forest_ne_RC'
            outward_dir: 'east' for NE/SE grids, 'west' for NW/SW grids
            anchor_row:  row number (1-5) holding the procedural passage
                         at col 4; that room's outward exit is skipped.
        """
        # Outer col 4 (outward edge)
        for r in range(1, 6):
            if r == anchor_row:
                continue  # procedural exit owns this direction
            room = rooms[f"{prefix}{r}4"]
            target = rooms[f"{prefix}{r}2"]  # 2 rooms inward
            connect_oneway_loopback_exit(room, outward_dir, destination=target)

        # North edge (row 1), cols 2-4
        for c in range(2, 5):
            room = rooms[f"{prefix}1{c}"]
            target = rooms[f"{prefix}3{c}"]  # 2 rows south (inward)
            connect_oneway_loopback_exit(room, "north", destination=target)

        # South edge (row 5), cols 2-4
        for c in range(2, 5):
            room = rooms[f"{prefix}5{c}"]
            target = rooms[f"{prefix}3{c}"]  # 2 rows north (inward)
            connect_oneway_loopback_exit(room, "south", destination=target)

    # NE: outward = east, procedural anchor at ne_24
    _wire_grid_loopbacks("forest_ne_", "east", anchor_row=2)
    # NW: outward = west, procedural anchor at nw_54
    _wire_grid_loopbacks("forest_nw_", "west", anchor_row=5)
    # SE: outward = east, procedural anchor at se_34
    _wire_grid_loopbacks("forest_se_", "east", anchor_row=3)
    # SW: outward = west, procedural anchor at sw_44
    _wire_grid_loopbacks("forest_sw_", "west", anchor_row=4)


# ── Gnoll Territory (5 rooms) ────────────────────────────────────

    rooms["wild_grasslands"] = create_object(
        RoomBase,
        key="Wild Grasslands",
        attributes=[
            ("desc",
             "The cultivated land ends and open grasslands begin — "
             "waist-high grass stretching to the horizon under a wide, "
             "empty sky. The wind moves through the grass in long, "
             "slow waves. There are no fences here, no walls, no "
             "signs of human settlement. Old cart tracks, barely "
             "visible, suggest a road once ran through here. The "
             "grass is trampled in places by heavy, clawed feet."),
        ],
    )

    connect_bidirectional_exit(rooms["forest_track_13"], rooms["wild_grasslands"], "south")

    rooms["wild_grasslands"].details = {
        "tracks": (
            "Broad, three-toed prints pressed deep into the soft "
            "earth — gnoll tracks, and recent ones. They come from "
            "the south in loose, irregular groups. Scouts, or the "
            "vanguard of a raiding party."
        ),
        "grass": (
            "Tall and tough, the grass here has gone wild for years. "
            "It rustles constantly in the wind, making it impossible "
            "to hear anything approaching until it's close. Perfect "
            "ambush country."
        ),
    }

    rooms["gnoll_hunting_grounds"] = create_object(
        RoomBase,
        key="Gnoll Hunting Grounds",
        attributes=[
            ("desc",
             "The grasslands here are criss-crossed with gnoll trails "
             "— trampled paths worn through the tall grass by repeated "
             "patrols. Bones are scattered in the grass: deer, rabbit, "
             "and some that might be human. A crude marker — a stick "
             "driven into the ground with a skull lashed to the top — "
             "stands at a trail junction, a territorial warning. The "
             "stench of gnoll musk hangs in the air, sharp and acrid. "
             "To the east, a low hill rises above the grass."),
        ],
    )
    rooms["gnoll_hunting_grounds"].details = {
        "bones": (
            "Cracked and gnawed, the bones are scattered carelessly "
            "in the grass — the remains of gnoll meals. Most are "
            "animal, but a cracked human femur and a jawbone with "
            "gold fillings tell a grimmer story."
        ),
        "marker": (
            "A sharpened stick driven into the earth, with a sun-"
            "bleached skull tied to the top with sinew. Gnoll "
            "territory markers — a clear warning to anything with "
            "the sense to read it. The skull is human."
        ),
    }

    rooms["ravaged_farmstead"] = create_object(
        RoomBase,
        key="Ravaged Farmstead",
        attributes=[
            ("desc",
             "The burnt-out shell of a farmstead stands in a trampled "
             "clearing. The buildings have been torn apart — walls "
             "smashed, roof timbers pulled down, everything of value "
             "looted or destroyed. Claw marks gouge the remaining "
             "doorframes, and the blackened stones of the hearth are "
             "the only part of the house still standing. This wasn't "
             "abandoned — it was attacked. The destruction has the "
             "frenzied, wasteful quality of gnoll raiders who destroy "
             "for the joy of it."),
        ],
    )
    rooms["ravaged_farmstead"].details = {
        "claw_marks": (
            "Deep gouges raked through the wood of the doorframes — "
            "four parallel lines, spaced wider than a human hand. "
            "Gnoll claws, driven by malice rather than purpose. They "
            "marked everything they could reach."
        ),
        "hearth": (
            "The stone hearth stands alone amid the wreckage, smoke-"
            "blackened and cracked from the fire that consumed the "
            "house. An iron cooking pot, too heavy to carry, still "
            "sits in the ashes. Someone lived here. Someone cooked "
            "meals and warmed their hands at this fire."
        ),
    }

    rooms["gnoll_camp"] = create_object(
        RoomBase,
        key="Gnoll Camp",
        attributes=[
            ("desc",
             "A gnoll encampment sprawls across a shallow depression "
             "in the grasslands, sheltered from the wind. Hide tents "
             "are stretched over frames of lashed bones and green "
             "wood, their surfaces daubed with crude symbols in red "
             "and black pigment. A central firepit holds the charred "
             "remains of something large, and racks of drying meat "
             "stand nearby. The stench is appalling — gnolls have no "
             "concept of sanitation. Crude weapons and stolen goods "
             "are piled haphazardly around the camp."),
        ],
    )
    rooms["gnoll_camp"].details = {
        "tents": (
            "Hides stretched over frames of bone and wood, stitched "
            "with sinew. The symbols painted on them are crude but "
            "consistent — clan markings, perhaps, or religious icons. "
            "Each tent reeks of gnoll musk and rotting food."
        ),
        "firepit": (
            "A broad, shallow pit ringed with blackened stones. The "
            "charred remains in the center are too large to be animal "
            "and too burnt to identify with certainty. Best not to "
            "think about it."
        ),
        "goods": (
            "Stolen from raids on the farmsteads and travellers: "
            "sacks of grain, bolts of cloth, tools, and a few items "
            "of jewellery. The gnolls don't understand the value of "
            "most of it — they hoard instinctively, like crows "
            "collecting shiny things."
        ),
    }

    rooms["gnoll_lookout"] = create_object(
        RoomBase,
        key="Gnoll Lookout",
        attributes=[
            ("desc",
             "A low rise south of the gnoll camp, where the grass "
             "has been beaten flat by gnoll sentries. A crude platform "
             "of lashed timbers gives a view across the southern "
             "grasslands. Gnoll sentries watch from here, their "
             "hyena-like faces scanning the horizon for threats — or "
             "prey. The platform is strewn with gnawed bones and "
             "discarded weapons."),
        ],
    )
    rooms["gnoll_lookout"].details = {
        "platform": (
            "Rough timbers lashed with rope and sinew, barely stable "
            "enough to stand on. The gnolls who built it were strong "
            "but not skilled — the whole structure creaks and sways "
            "in the wind. It gives a commanding view south, toward "
            "the Shadowsward."
        ),
    }

    # ── Barrow Underground (5 rooms) ─────────────────────────────────

    rooms["barrow_hill"] = create_object(
        RoomBase,
        key="Barrow Hill",
        attributes=[
            ("desc",
             "A low, grass-covered hill rises from the plains east "
             "of the gnoll trails. It is oddly symmetrical — too "
             "regular to be natural, though centuries of wind and "
             "rain have softened its lines. Thorn bushes and nettles "
             "grow thick on its slopes, and a standing stone, tilted "
             "with age, marks the summit. The gnolls avoid this place "
             "— their trails give it a wide berth. The air here "
             "feels heavy, watchful, as though something beneath the "
             "hill is aware of your presence."),
        ],
    )
    rooms["barrow_hill"].details = {
        "stone": (
            "A standing stone of dark granite, roughly five feet tall "
            "and tilted fifteen degrees from vertical. Faint geometric "
            "carvings cover its surface — the same interlocking circles "
            "and angular spirals found in the deep sewers and the "
            "sealed door in the abandoned mine. The stone is cold to "
            "the touch, even in direct sunlight."
        ),
        "hill": (
            "The hill is perhaps thirty feet high and perfectly "
            "oval, its long axis running east-west. The grass grows "
            "thicker here than on the surrounding plains, as though "
            "fed by something beneath the soil. It is a barrow — an "
            "ancient burial mound — though who built it and what "
            "lies inside is unclear."
        ),
    }

    rooms["barrow_entrance"] = create_object(
        RoomBase,
        key="Barrow Entrance",
        attributes=[
            ("desc",
             "A narrow passage descends into the heart of the barrow "
             "through walls of dry-fitted stone. The air turns cold "
             "immediately, and the smell of earth and old bone rises "
             "from below. The stonework is ancient — enormous blocks "
             "fitted without mortar, their surfaces carved with faint "
             "geometric patterns that seem to shift in the torchlight. "
             "Cobwebs span the passage in thick curtains, and the "
             "silence is absolute."),
        ],
    )
    rooms["barrow_entrance"].details = {
        "stonework": (
            "The same precision-fitted blocks found in the mine's "
            "ancient passage and the deep sewers. No chisel marks, "
            "no mortar, no visible means of construction. The "
            "geometric patterns are shallow but sharp-edged, as "
            "though carved yesterday despite being centuries old."
        ),
        "cobwebs": (
            "Thick, grey curtains of ancient webbing, undisturbed "
            "for years. Whatever spun them is either long dead or "
            "has moved deeper. The webs tear apart with a dry, "
            "papery sound."
        ),
    }

    rooms["bone_passage"] = create_object(
        RoomBase,
        key="Bone-Strewn Passage",
        attributes=[
            ("desc",
             "The passage widens into a corridor lined with stone "
             "shelves carved into the walls, each holding the remains "
             "of the ancient dead. Most are dust and fragments, but "
             "some skeletons remain eerily intact, their bones "
             "yellowed and brittle. A cold draught stirs the air, "
             "carrying a faint sound — scratching, or shuffling, "
             "from somewhere ahead. Not all the dead here rest "
             "quietly. Scattered on the floor are bones that have "
             "been disturbed — pulled from their shelves, arranged, "
             "and discarded. Someone has been working down here."),
        ],
    )
    rooms["bone_passage"].details = {
        "bones": (
            "The bones on the floor have been sorted — skulls in "
            "one pile, long bones in another, small fragments swept "
            "aside. This is not the work of animals or grave robbers. "
            "Someone with knowledge and purpose has been cataloguing "
            "the dead."
        ),
        "shelves": (
            "Stone shelves carved directly from the walls, each "
            "sized for a single body. Most hold only dust and "
            "fragments. A few contain intact skeletons laid out "
            "with care — arms folded, jaws closed, positioned as "
            "though sleeping. These are very old burials."
        ),
    }

    rooms["ancient_catacombs"] = create_object(
        RoomBase,
        key="Ancient Catacombs",
        attributes=[
            ("desc",
             "The passage opens into a vaulted chamber of worked "
             "stone, its ceiling lost in shadow above. The walls are "
             "covered floor to ceiling with geometric carvings — the "
             "same interlocking circles and angular spirals found at "
             "the sealed door in the abandoned mine, but here they "
             "cover entire walls in vast, repeating patterns. The "
             "carvings pulse with a faint luminescence, casting pale "
             "blue-white light across the chamber. Stone sarcophagi "
             "line the walls, their lids carved with the same "
             "geometric motifs. The hum is audible here — a deep, "
             "resonant vibration that rises from the stone itself."),
        ],
    )
    rooms["ancient_catacombs"].details = {
        "carvings": (
            "The geometric patterns are identical to those in the "
            "mine's ancient passage and the deep sewers — proof that "
            "the same civilisation built all three. Here, the "
            "patterns cover entire walls in intricate, recursive "
            "designs that seem to encode information. The faint "
            "luminescence pulses in slow waves, like breathing."
        ),
        "sarcophagi": (
            "Heavy stone coffins, sealed and undisturbed — except "
            "for one. A single sarcophagus in the far corner has "
            "been opened, its lid pushed aside. Inside, the bones "
            "have been carefully removed and replaced with books, "
            "scrolls, and glass bottles. Someone is using this "
            "as a storage chest."
        ),
        "hum": (
            "The vibration rises from the floor, the walls, the "
            "very air. It is felt in the teeth and the bones more "
            "than heard with the ears. It intensifies near the "
            "carved walls and fades in the center of the chamber. "
            "The same hum exists at the sealed door in the mine."
        ),
    }

    rooms["necromancers_study"] = create_object(
        RoomBase,
        key="Necromancer's Study",
        attributes=[
            ("desc",
             "A chamber at the back of the catacombs, fitted out as "
             "a working study with stolen furniture and improvised "
             "shelving. A heavy desk is covered with open books, "
             "anatomical sketches, and jars of preserved specimens. "
             "Bookshelves line one wall, crammed with volumes on "
             "death magic, anatomy, and the history of the Ancient "
             "Builders. Candles burn in skull-shaped holders, casting "
             "flickering light across a workspace that is organised, "
             "methodical, and deeply unsettling. The occupant of this "
             "study is clearly intelligent, patient, and utterly "
             "unconcerned with the moral implications of their work."),
        ],
    )
    rooms["necromancers_study"].details = {
        "desk": (
            "A solid oak desk, probably stolen from a farmhouse. "
            "It is covered with open grimoires, hand-drawn diagrams "
            "of skeletal anatomy, and careful notes in a precise, "
            "cramped hand. The notes reference 'reanimation energies' "
            "and 'the residual will of the ancient dead' with the "
            "clinical detachment of a scholar, not a madman."
        ),
        "books": (
            "A serious collection — not the theatrical props of a "
            "hedge wizard but genuine academic texts on necromancy, "
            "the nature of death, and the history of the civilisation "
            "that built these catacombs. Several volumes bear the "
            "seal of the Mages' Guild library. They were not borrowed."
        ),
        "specimens": (
            "Glass jars containing preserved organs, bone fragments, "
            "and things less identifiable, each neatly labelled in "
            "the same cramped handwriting. Research materials, not "
            "trophies. The preservation is expert — this is someone "
            "who knows their craft."
        ),
    }

    # ── Shadowsward (2 rooms) ──────────────────────────────────────────

    rooms["southern_approach"] = create_object(
        RoomBase,
        key="Southern Approach",
        attributes=[
            ("desc",
             "The old road reappears beyond the gnoll territory — a "
             "faded track running south through increasingly wild "
             "grasslands. The ground rises gently toward a ridge, "
             "and on the ridge stands a gate — a proper stone "
             "gatehouse straddling the road, its towers crumbling "
             "but its arch still intact. Whatever lies beyond that "
             "gate is another country entirely. The wind from the "
             "south carries unfamiliar scents — dry earth, distant "
             "smoke, and something feral."),
        ],
    )

    rooms["shadowsward_gate"] = create_object(
        RoomGateway,
        key="Shadowsward Gate",
        attributes=[
            ("desc",
             "A crumbling stone gatehouse marks the southern boundary "
             "of Millholm's territory. The iron portcullis is rusted "
             "in its half-lowered position, leaving a gap beneath "
             "that a person could squeeze through — but beyond it, "
             "the road descends into lands that Millholm's maps do "
             "not cover. The Shadowsward stretches to the horizon, "
             "wild and uncharted. A weathered stone marker beside "
             "the gate reads: 'HERE ENDS THE PROTECTION OF THE "
             "MILLHOLM GUARD.' Someone has scratched beneath it: "
             "'and here begins the fun.'"),
        ],
    )
    rooms["shadowsward_gate"].details = {
        "portcullis": (
            "Rusted iron bars, thick as a man's wrist, frozen in "
            "place by decades of corrosion. The gap beneath is just "
            "large enough to crawl through, but the land beyond "
            "looks empty and hostile. Only the bold or the desperate "
            "would pass this way unprepared."
        ),
        "marker": (
            "A stone pillar carved with the seal of Millholm — a "
            "sheaf of wheat crossed with a pickaxe. The official "
            "warning is carved in formal script. The graffiti below "
            "is scratched in a looser hand, the work of an adventurer "
            "who came this way and lived to joke about it."
        ),
    }

    print(f"  Created {len(rooms)} rooms.")





    connect_bidirectional_exit(rooms["wild_grasslands"], rooms["gnoll_hunting_grounds"], "south")
    connect_bidirectional_exit(rooms["gnoll_hunting_grounds"], rooms["ravaged_farmstead"], "west")
    connect_bidirectional_exit(rooms["gnoll_hunting_grounds"], rooms["gnoll_camp"], "south")
    connect_bidirectional_exit(rooms["gnoll_camp"], rooms["gnoll_lookout"], "south")

    # ── Barrow (hidden entrance) ─────────────────────────────────────
    connect_bidirectional_exit(rooms["gnoll_hunting_grounds"], rooms["barrow_hill"], "east")

    # Hidden door from barrow hill into the barrow entrance
    door_ab, door_ba = connect_bidirectional_door_exit(
        rooms["barrow_hill"], rooms["barrow_entrance"], "down",
        key="a dark opening",
        closed_ab=(
            "The hillside is covered in dense thorn bushes and nettles. "
            "Nothing remarkable is visible."
        ),
        open_ab=(
            "A dark opening in the hillside is visible between the "
            "thorn bushes, descending into the earth."
        ),
        closed_ba=(
            "The passage upward is blocked by a tangle of thorns "
            "and roots."
        ),
        open_ba=(
            "Daylight filters down through an opening in the hillside "
            "above."
        ),
        door_name="opening",
    )
    door_ab.is_hidden = True
    door_ab.find_dc = 15

    # Barrow interior
    connect_bidirectional_exit(rooms["barrow_entrance"], rooms["bone_passage"], "south")
    connect_bidirectional_exit(rooms["bone_passage"], rooms["ancient_catacombs"], "south")
    connect_bidirectional_exit(rooms["ancient_catacombs"], rooms["necromancers_study"], "south")

    # ── Shadowsward ────────────────────────────────────────────────────
    # Path continues south past gnoll territory
    connect_bidirectional_exit(rooms["gnoll_lookout"], rooms["southern_approach"], "south")
    connect_bidirectional_exit(rooms["southern_approach"], rooms["shadowsward_gate"], "south")

    print("  Exits wired.")

    # ══════════════════════════════════════════════════════════════════
    # 3. TAG ROOMS — zone, district, terrain, mob_area
    # ══════════════════════════════════════════════════════════════════

    # ── Zone + District ──
    # Applied to every room in the builder (including disconnected
    # legacy carryover) so clean_zone() can find them for teardown.
    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # ── Terrain ──
    # Rural: road/farmyard-style ground
    for key in ["countryside_road", "farmstead_fork"]:
        rooms[key].set_terrain(TerrainType.RURAL.value)

    # Forest: everything woodland — track, grids, approach trails,
    # moonpetal edges, sage clearing features
    _forest_keys = [
        "forests_edge",
        *[f"forest_track_{i}" for i in range(1, 14)],
        *[f"forest_ne_{r}{c}" for r in range(1, 6) for c in range(1, 5)],
        *[f"forest_nw_{r}{c}" for r in range(1, 6) for c in range(1, 5)],
        *[f"forest_se_{r}{c}" for r in range(1, 6) for c in range(1, 5)],
        *[f"forest_sw_{r}{c}" for r in range(1, 6) for c in range(1, 5)],
        # Bobbin approach
        "bobbin_goode_interface_room_forest", "bobbin_goode_interface_room_moonpetal_2",
        "bobbin_north_trail", "bobbin_forest_trail",
        # Moonpetal interfaces + edges (fringe woodland)
        "moonpetal1_interface_room_forest", "moonpetal1_interface_room_raven_sage",
        "moonpetal1_edge_north", "moonpetal1_edge_south",
        "moonpetal1_edge_east", "moonpetal1_edge_west",
        "moonpetal2_interface_room_forest", "moonpetal2_interface_room_bobbin_goode",
        "moonpetal2_edge_north", "moonpetal2_edge_south",
        "moonpetal2_edge_east", "moonpetal2_edge_west",
        # Sage clearing features
        "raven_sage_interface_room_forest", "raven_sage_interface_room_moonpetal1",
        "raven_standing_stones", "raven_yew_grove", "raven_tree", "raven_herb_garden",
    ]
    for key in _forest_keys:
        rooms[key].set_terrain(TerrainType.FOREST.value)

    # Plains: open meadow of the moonpetal main clearings
    for key in ["moonpetal1_main", "moonpetal2_main"]:
        rooms[key].set_terrain(TerrainType.PLAINS.value)

    # Rural: Bobbin's camp (patched farmstead) + sage's hut interior
    _camp_and_hut_keys = [
        "bobbin_holdfast_gate", "bobbin_stable", "bobbin_yard", "bobbin_watchtower",
        "bobbin_common_fire", "bobbin_barracks", "bobbin_barn_stores",
        "bobbin_kitchen", "bobbin_training_yard",
        "bobbin_planning_tent", "bobbin_quarters",
        "raven_hut_porch", "raven_hut_study", "raven_hut_workshop",
        "raven_hut_bedchamber",
    ]
    for key in _camp_and_hut_keys:
        rooms[key].set_terrain(TerrainType.RURAL.value)

    # Underground: sage's cellar + legacy barrow interior
    _underground_keys = [
        "raven_hut_cellar",
        "barrow_entrance", "bone_passage",
        "ancient_catacombs", "necromancers_study",
    ]
    for key in _underground_keys:
        rooms[key].set_terrain(TerrainType.UNDERGROUND.value)

    # Legacy carryover — gnoll territory + barrow + shadowsward were
    # kept in the new build as a placeholder at the south end of the
    # track, pending a proper redesign. (bandit_holdfast, bandit_camp,
    # moonpetal_approach, and the old moonpetal grid are NOT carried
    # over — they live only in southern_old.py for reference.)
    _legacy_plains = [
        "wild_grasslands", "gnoll_hunting_grounds",
        "ravaged_farmstead", "gnoll_camp", "gnoll_lookout",
        "barrow_hill",
        "southern_approach", "shadowsward_gate",
    ]
    for key in _legacy_plains:
        rooms[key].set_terrain(TerrainType.PLAINS.value)

    # ── mob_area tags ──
    # Planning tags for future mob placement. These tags currently have
    # NO spawn rules, so no mobs will spawn in the new areas — the tags
    # are a placeholder for when wolf packs, bandits, etc. are designed.
    #
    # gnoll_territory / gnoll_camp_boss (which DO have live spawn rules
    # in world/spawns/millholm_southern.json) are intentionally NOT
    # applied — the legacy gnoll rooms are parked until a redesign.

    # Wolves — one pack per forest chunk (1 direwolf alpha + 3 southern wolves)
    for r in range(1, 6):
        for c in range(1, 5):
            rooms[f"forest_ne_{r}{c}"].tags.add("wolves_ne", category="mob_area")
            rooms[f"forest_nw_{r}{c}"].tags.add("wolves_nw", category="mob_area")
            rooms[f"forest_se_{r}{c}"].tags.add("wolves_se", category="mob_area")
            rooms[f"forest_sw_{r}{c}"].tags.add("wolves_sw", category="mob_area")

    # Pack den rooms — alpha respawns here; followers fall back here when
    # the alpha is dead. Center of each 5×4 quadrant grid (r=3, c=3).
    rooms["forest_ne_33"].tags.add("wolves_ne_den", category="mob_area")
    rooms["forest_nw_33"].tags.add("wolves_nw_den", category="mob_area")
    rooms["forest_se_33"].tags.add("wolves_se_den", category="mob_area")
    rooms["forest_sw_33"].tags.add("wolves_sw_den", category="mob_area")

    # Raven flock — 8 ravens pinned to the great oak.
    rooms["raven_tree"].tags.add("raven_tree_flock", category="mob_area")

    # Corren the Sage — wanders slowly between Study, Hut Porch,
    # Standing Stones, and Herb Garden.
    for key in (
        "raven_hut_study",
        "raven_hut_porch",
        "raven_standing_stones",
        "raven_herb_garden",
    ):
        rooms[key].tags.add("corren_haunts", category="mob_area")

    # Moonpetal meadows — butterfly ambience. Both clearings + their
    # edges share one tag; interfaces stay untagged so butterflies don't
    # drift out into the woods.
    _moonpetal_meadow_keys = [
        "moonpetal1_main",
        "moonpetal1_edge_north", "moonpetal1_edge_south",
        "moonpetal1_edge_east", "moonpetal1_edge_west",
        "moonpetal2_main",
        "moonpetal2_edge_north", "moonpetal2_edge_south",
        "moonpetal2_edge_east", "moonpetal2_edge_west",
    ]
    for key in _moonpetal_meadow_keys:
        rooms[key].tags.add("moonpetal_meadow", category="mob_area")

    # Bandit ambush — the ravine proper (tightened to just the
    # chokepoint room; approach/exit rooms left untagged, pending a
    # future ambush design pass which may re-scope this).
    rooms["forest_track_7"].tags.add("bandit_ambush", category="mob_area")

    # Bobbin's camp — general bandit pool (chorus, generic mooks).
    # Kitchen, stable, and barracks are safe-zone rooms (no combat) and
    # are intentionally excluded from the spawn pool.
    _bandit_camp_keys = [
        "bobbin_yard", "bobbin_common_fire",
        "bobbin_barn_stores", "bobbin_training_yard",
        "bobbin_planning_tent",
    ]
    for key in _bandit_camp_keys:
        rooms[key].tags.add("bandit_camp", category="mob_area")

    # Blynken's post — the lookout. Already-existing bandit_lookout tag
    # is the pin point.
    rooms["bobbin_watchtower"].tags.add("bandit_lookout", category="mob_area")

    # Bobbin Goode's personal spawn — pinned to Common Fire so the
    # entry song-and-introduction routine fires in the right place.
    rooms["bobbin_common_fire"].tags.add("bandit_camp_leader", category="mob_area")

    # Bobbin's Quarters — reputation-gated inner sanctum (future)
    rooms["bobbin_quarters"].tags.add("bandit_camp_inner", category="mob_area")

    # Named-lieutenant pin tags — one room per lieutenant so each
    # spawn rule (target=1, max_per_room=1) lands in exactly one place.
    rooms["bobbin_training_yard"].tags.add("bandit_lieutenant_john", category="mob_area")
    rooms["bobbin_yard"].tags.add("bandit_lieutenant_will", category="mob_area")
    rooms["bobbin_kitchen"].tags.add("bandit_friar", category="mob_area")
    rooms["bobbin_planning_tent"].tags.add("bandit_maid", category="mob_area")

    # ── Sheltered flag (indoor weather behaviour) ──
    # Rooms with real cover — roofed, walled, or under canvas — treated
    # as indoor for weather (muffled only, no rain effects). Outdoor
    # spaces (yards, firepits, gates, trails, roads) inherit the default
    # exposed behaviour from their terrain type.
    _sheltered_keys = [
        # Bobbin's camp — roofed/tented structures
        "bobbin_stable", "bobbin_watchtower",
        "bobbin_barracks", "bobbin_barn_stores",
        "bobbin_kitchen", "bobbin_planning_tent",
        "bobbin_quarters",
        # Sage's hut interior
        "raven_hut_study", "raven_hut_workshop", "raven_hut_bedchamber",
    ]
    for key in _sheltered_keys:
        rooms[key].sheltered = True

    # ── Sleep policy ─────────────────────────────────────────────────
    # Super sleep (5x regen) — the barracks is where camp residents
    # bed down; players welcomed into the camp share the same regen.
    rooms["bobbin_barracks"].set_sleep_policy("super")

    # ── Combat flags ─────────────────────────────────────────────────
    # Barracks is a sleeping room — no combat so resting players
    # can't be attacked in their bedroll.
    rooms["bobbin_barracks"].allow_combat = False

    print("  Tagged rooms with zone, district, terrain, and mob_area.")

    # ── Region map cell tags ────────────────────────────────────────
    _rt = "millholm_region"

    # Spine — entry into the forest
    for key in ["countryside_road", "farmstead_fork", "forests_edge"]:
        rooms[key].tags.add(f"{_rt}:forests_edge_cell", category="map_cell")

    # Spine — northern forest track (Game Trail → Trail Descent)
    for key in ["forest_track_1", "forest_track_2", "forest_track_3", "forest_track_4"]:
        rooms[key].tags.add(f"{_rt}:forest_path_n", category="map_cell")

    # Spine — ravine: tags 3 cells (path + west/east mid wilderness)
    for key in ["forest_track_5", "forest_track_6", "forest_track_7", "forest_track_8"]:
        for cell in ["forest_path_ravine", "forest_mid_w", "forest_mid_e"]:
            rooms[key].tags.add(f"{_rt}:{cell}", category="map_cell")

    # Spine — southern forest track (Old Wood → Trail's End)
    for key in ["forest_track_9", "forest_track_10", "forest_track_11", "forest_track_12"]:
        rooms[key].tags.add(f"{_rt}:forest_path_s", category="map_cell")

    # Forest Edge (south) + grasslands
    for key in ["forest_track_13", "wild_grasslands"]:
        rooms[key].tags.add(f"{_rt}:grasslands", category="map_cell")

    # Gnoll territory + barrow surface
    for key in ["gnoll_hunting_grounds", "gnoll_camp", "ravaged_farmstead",
                "barrow_hill", "gnoll_lookout"]:
        rooms[key].tags.add(f"{_rt}:gnoll_camp", category="map_cell")

    # Barrow underground
    for key in ["barrow_entrance", "bone_passage", "ancient_catacombs",
                "necromancers_study"]:
        rooms[key].tags.add(f"{_rt}:barrow_underground", category="map_cell")

    # Shadowsward gate (also includes the approach road)
    for key in ["southern_approach", "shadowsward_gate"]:
        rooms[key].tags.add(f"{_rt}:shadowsward_gate", category="map_cell")

    # Forest grids — 4 quadrants, 20 rooms each
    _grid_cells = {
        "forest_nw_": "forest_nw",
        "forest_ne_": "forest_ne",
        "forest_sw_": "forest_sw",
        "forest_se_": "forest_se",
    }
    for room_key, room in rooms.items():
        for prefix, cell in _grid_cells.items():
            if room_key.startswith(prefix):
                room.tags.add(f"{_rt}:{cell}", category="map_cell")
                break

    # Mini-areas — Bobbin Goode camp
    for room_key, room in rooms.items():
        if room_key.startswith("bobbin_"):
            room.tags.add(f"{_rt}:bobbin_camp", category="map_cell")

    # Mini-areas — Raven sage hermitage
    for room_key, room in rooms.items():
        if room_key.startswith("raven_"):
            room.tags.add(f"{_rt}:raven_sage", category="map_cell")

    # Mini-areas — Moonpetal clearings
    for room_key, room in rooms.items():
        if room_key.startswith("moonpetal1_"):
            room.tags.add(f"{_rt}:moonpetal_1", category="map_cell")
        elif room_key.startswith("moonpetal2_"):
            room.tags.add(f"{_rt}:moonpetal_2", category="map_cell")

    print(f"  Tagged southern rooms with {_rt} map_cell tags.")

    return rooms
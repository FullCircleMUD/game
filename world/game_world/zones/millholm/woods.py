"""
Millholm Woods — the forest district east of Millholm Town.

Builds ~93 rooms including:
- Forest Path East (interface room connecting to town's road_far_east)
- Main winding path (17 rooms, east through light woods to wooded foothills)
- Sawmill spur (2 rooms north of Edge of Woods, RoomProcessing: wood→timber)
- Smelter spur (2 rooms south of Edge of Woods, RoomProcessing: ores→ingots)
- Southern woods grid (10 wide × 6 deep = 60 rooms) with:
  - Edge self-loops on west/east/south boundaries (forest turns you back)
  - Notable POI rooms: Game Trail Crossing, Stone Cairn, Fallen Giant,
    Berry Bramble, Rabbit Warren, Trapper's Hut, Fox Earth, Spring-fed Pool
  - North edge connects to main path rooms 5-14
- Northern woods row (10 Dense Woods rooms north of main path rooms 5-14):
  - Denser transition woods; all funnel north into one entry room
- Deep Woods Entry (Edge of the Deep Woods):
  - All 10 northern rooms converge here via one-way north exits
  - South exit returns to middle of the northern row
  - North: procedural passage to deep_woods_clearing (wired in build_game_world)

Usage:
    from world.game_world.millholm_woods import build_millholm_woods
    build_millholm_woods(town_rooms)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from typeclasses.terrain.rooms.room_processing import RoomProcessing
from utils.exit_helpers import connect_bidirectional_exit, connect_oneway_loopback_exit


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_woods"

# ── 10×6 Southern Woods grid room data ────────────────────────────────
# Each entry: (room_key, long_description)
# Row 1 = northmost (connects to main path), Row 6 = south boundary.

GRID_ROOMS = [
    # ── Row 1 ──────────────────────────────────────────────────────
    [
        ("Quiet Woods",
         "Leafy undergrowth muffles sound in these quiet woods. Game "
         "trails crisscross subtly beneath a thinning canopy."),
        ("Quiet Woods",
         "Low brambles and scattered ferns mark a seldom-used way "
         "through the trees. Birds flit unseen."),
        ("Quiet Woods",
         "The forest floor is a patchwork of leaf litter and root, "
         "with faint signs of passage."),
        ("Quiet Woods",
         "A stand of hazel creates a sparse screen. The undergrowth "
         "parts where animals have passed."),
        ("Quiet Woods",
         "Sun-dappled patches mark a gentler openness beneath the "
         "trees."),
        ("Quiet Woods",
         "Fallen twigs snap underfoot. Small tracks fade into the "
         "brush."),
        ("Quiet Woods",
         "The scent of resin and damp earth hangs in the still air."),
        ("Quiet Woods",
         "Sparse shrubs allow long sightlines between trunks."),
        ("Quiet Woods",
         "Here the ground is firm and the brush low, a favored path "
         "for deer."),
        ("Quiet Woods",
         "Wind worries the leaves overhead, but it's hushed at the "
         "forest floor."),
    ],
    # ── Row 2 ──────────────────────────────────────────────────────
    [
        ("Game Trail Crossing",
         "Two game trails intersect here, the ground pressed flat by "
         "hooves and padded feet."),
        ("Quiet Woods",
         "Thorny bramble patches encourage a careful step."),
        ("Stone Cairn",
         "A low cairn of mossy stones suggests a marker "
         "long-forgotten."),
        ("Quiet Woods",
         "The canopy thickens briefly, casting a green gloom."),
        ("Fallen Giant",
         "A giant fallen trunk lies rotting, its bark peeling to "
         "reveal pale wood beneath."),
        ("Quiet Woods",
         "Twig snaps and distant rustles hint at unseen wildlife."),
        ("Berry Bramble",
         "A wide bramble patch promises berries in season and "
         "scratched hands regardless."),
        ("Quiet Woods",
         "Leaf mold and mushrooms flourish in the dimness."),
        ("Rabbit Warren",
         "Small burrow mouths pock the ground; a rabbit warren lies "
         "beneath."),
        ("Quiet Woods",
         "Sunlight pools and fades with each sway of the higher "
         "branches."),
    ],
    # ── Row 3 (Trapper's Hut at C4) ───────────────────────────────
    [
        ("Quiet Woods",
         "A tangle of saplings leans into a narrow clearing."),
        ("Old Snare Line",
         "Old snare stakes and faint cord impressions betray a "
         "trapper's route."),
        ("Quiet Woods",
         "The forest hush returns, disturbed only by the occasional "
         "birdcall."),
        ("Trapper's Hut",
         "A rough-hewn hut stands among the trees, pelts stretched "
         "to dry on frames. The smell of smoke and tannin lingers "
         "in the air."),
        ("Quiet Woods",
         "Worn footfalls have pressed a subtle route through brush "
         "and leaf."),
        ("Hollow Log",
         "A long-dead log lies hollowed and mossy, home to beetles "
         "and salamanders."),
        ("Quiet Woods",
         "Cool air flows along a barely perceptible dip in the "
         "ground."),
        ("Spring-fed Pool",
         "A shallow pool mirrors the canopy; a small spring bubbles "
         "at its edge."),
        ("Quiet Woods",
         "A patch of soft moss makes an inviting, if damp, resting "
         "place."),
        ("Quiet Woods",
         "Tree roots knot across the ground like cables beneath the "
         "leaf litter."),
    ],
    # ── Row 4 (Fox Earth at C2) ────────────────────────────────────
    [
        ("Quiet Woods",
         "The woods close in a little here, branches interlacing "
         "overhead."),
        ("Fox Earth",
         "A low earthy mound, pocked with narrow burrow entrances, "
         "sits beneath a gnarled root. The sharp musk of fox hangs "
         "in the air, and tufts of russet fur cling to the dirt rim."),
        ("Quiet Woods",
         "Faint claw marks score a nearby trunk."),
        ("Quiet Woods",
         "A cluster of toadstools dots the damp earth."),
        ("Quiet Woods",
         "The ground dips here, holding last night's dew a little "
         "longer."),
        ("Quiet Woods",
         "Old leaves crackle underfoot, dry despite the shade."),
        ("Quiet Woods",
         "Sunlight splinters into golden motes around drifting "
         "seeds."),
        ("Quiet Woods",
         "A weathered stump provides a convenient seat."),
        ("Quiet Woods",
         "A faint animal track skirts around a thorny tangle."),
        ("Quiet Woods",
         "Patchy sunlight flickers across uneven ground."),
    ],
    # ── Row 5 ──────────────────────────────────────────────────────
    [
        ("Quiet Woods",
         "Saplings reclaim an old clearing, their tops brushing the "
         "lower branches."),
        ("Quiet Woods",
         "A trickle of water disappears into thirsty soil."),
        ("Quiet Woods",
         "The forest hush is nearly complete here, peaceful and "
         "unhurried."),
        ("Quiet Woods",
         "Fresh scat suggests deer passed only moments ago."),
        ("Quiet Woods",
         "A tangle of bracken fronds forces a slight detour."),
        ("Quiet Woods",
         "Old woodpecker holes pattern a dead trunk."),
        ("Quiet Woods",
         "Patches of heather brighten the forest floor with purple."),
        ("Quiet Woods",
         "A fox track zigzags through the softer ground."),
        ("Quiet Woods",
         "The scent of distant smoke makes the air taste of "
         "campfire."),
        ("Quiet Woods",
         "A ring of mushrooms circles a patch of darker soil."),
    ],
    # ── Row 6 (south boundary, south exits loop to self) ──────────
    [
        ("Quiet Woods",
         "Here the ground softens and the air grows stiller, the "
         "woods gently discouraging further travel south."),
        ("Quiet Woods",
         "A dense tangle of brush suggests you have reached the "
         "limit of easy going."),
        ("Quiet Woods",
         "The ground grows sandy here, footprints fading quickly."),
        ("Quiet Woods",
         "An impenetrable wall of blackberry blocks the far south."),
        ("Quiet Woods",
         "A shallow swale holds cool air and stubborn shade."),
        ("Quiet Woods",
         "A thicket of saplings trembles at the slightest breeze."),
        ("Quiet Woods",
         "The trees stand close, their roots braided like ropes "
         "across the soil."),
        ("Quiet Woods",
         "Deadfall litters the floor, deterring movement further "
         "south."),
        ("Quiet Woods",
         "A lattice of vines grips the understory tightly."),
        ("Quiet Woods",
         "The edge of the forest seems to fold back upon itself "
         "here."),
    ],
]

# ── Northern Woods row (10 rooms north of main path) ────────────────
# Denser, darker transition woods. All 10 funnel north into a single
# deep woods entry room — the gateway to the procedural deep woods.

NORTHERN_WOODS = [
    ("Dense Woods",
     "The trees grow taller and closer here, their trunks thick with "
     "ivy and lichen. The canopy blocks most of the daylight, casting "
     "everything in deep green shadow."),
    ("Dense Woods",
     "Gnarled roots knot across the ground, half-hidden beneath dead "
     "leaves. The undergrowth thickens noticeably, pressing close on "
     "all sides."),
    ("Dense Woods",
     "Old growth oaks loom overhead, their lower branches bare and "
     "skeletal. The brush between the trunks is dense and dark, "
     "discouraging any step off the faint path."),
    ("Dense Woods",
     "The air hangs heavy with the scent of damp earth and rotting "
     "wood. Thick ferns crowd the forest floor, and the light barely "
     "penetrates the woven canopy above."),
    ("Dense Woods",
     "Moss-covered trunks stand like pillars in the gloom. The "
     "ground is soft and yielding underfoot, muffling every footfall "
     "to silence."),
    ("Dense Woods",
     "Tangled briar and hawthorn hedge the narrow gaps between "
     "trees. Cobwebs glint in what little light filters through, "
     "and the woods feel watchful and close."),
    ("Dense Woods",
     "The forest presses in from every side, branches interlocking "
     "like fingers overhead. A faint animal track is the only sign "
     "that anything passes this way."),
    ("Dense Woods",
     "Deadfall litters the ground between ancient trunks, making "
     "footing treacherous. The canopy is so thick that rain would "
     "barely reach the forest floor."),
    ("Dense Woods",
     "Twisted trees lean at odd angles, their roots gripping mossy "
     "boulders. The shadows deepen ahead, and the birdsong of the "
     "lighter woods has fallen silent."),
    ("Dense Woods",
     "The last traces of easy woodland give way to dense, dark "
     "forest. Thick undergrowth and low-hanging branches force a "
     "careful, stooping passage between the trunks."),
]


def _self_loop(room, direction, desc=None):
    """Create an exit that leads back to the same room (forest boundary)."""
    return connect_oneway_loopback_exit(room, direction, key=desc)


def build_millholm_woods(town_rooms):
    """
    Build the Millholm Woods district.

    Args:
        town_rooms: Dict of room objects from build_millholm_town().
                    Needs town_rooms["road_far_east"] as connection point.
    """

    rooms = {}

    # ══════════════════════════════════════════════════════════════════
    # 1. CREATE ROOMS
    # ══════════════════════════════════════════════════════════════════

    # ── Interface room (connects to town) ──────────────────────────

    rooms["forest_path_east"] = create_object(
        RoomBase,
        key="Forest Path East",
        attributes=[
            ("desc",
             "The eastern extension of the trade road enters the edge of "
             "Millholm Woods, where towering oak and maple trees begin to "
             "crowd the roadway. Dappled sunlight filters through the "
             "canopy, creating shifting patterns on the packed earth path. "
             "The sounds of the town fade behind, replaced by rustling "
             "leaves and distant bird calls. Moss-covered stones mark the "
             "transition from civilized road to wilderness trail."),
        ],
    )

    # ── Main path (17 rooms, winding east through the woods) ───────

    rooms["edge_of_woods"] = create_object(
        RoomBase,
        key="Edge of the Woods",
        attributes=[
            ("desc",
             "A well-worn path leads through the woods, where the trees "
             "thin enough to let shafts of light paint the leaf-strewn "
             "ground. The way east grows quieter as the sounds of town "
             "fade behind you."),
        ],
    )

    rooms["birch_stand"] = create_object(
        RoomBase,
        key="Birch Stand",
        attributes=[
            ("desc",
             "A narrow path leads through the woods between pale-barked "
             "birches, their leaves whispering softly overhead. The track "
             "winds onward, inviting travel deeper beneath the canopy."),
        ],
    )

    rooms["mossy_bend"] = create_object(
        RoomBase,
        key="Mossy Bend",
        attributes=[
            ("desc",
             "The path leads through the woods and curves around a "
             "moss-slick log. Ferns crowd the edges of the trail, and "
             "the scent of damp earth rises with each step."),
        ],
    )

    rooms["creekside_crossing"] = create_object(
        RoomBase,
        key="Creekside Crossing",
        attributes=[
            ("desc",
             "A trodden path leads through the woods to a shallow creek, "
             "where flat stones make an easy crossing. The burble of "
             "water competes with birdsong in the branches."),
        ],
    )

    rooms["tall_canopy"] = create_object(
        RoomBase,
        key="Tall Canopy Way",
        attributes=[
            ("desc",
             "The path leads through the woods beneath towering oaks and "
             "maples. Sunlight filters in narrow beams, and the air "
             "carries the resinous scent of leaf and bark."),
        ],
    )

    rooms["shadowed_hollow"] = create_object(
        RoomBase,
        key="Shadowed Hollow",
        attributes=[
            ("desc",
             "Here the path leads through the woods into a shallow "
             "hollow, where shadows linger even at midday. The ground is "
             "soft underfoot, cushioned by years of fallen leaves."),
        ],
    )

    rooms["split_trunk_oak"] = create_object(
        RoomBase,
        key="Split-trunk Oak",
        attributes=[
            ("desc",
             "A steady path leads through the woods past a massive oak "
             "split by lightning long ago. Fresh shoots crown the scar, "
             "and the trail squeezes between brambly undergrowth."),
        ],
    )

    rooms["fern_carpet"] = create_object(
        RoomBase,
        key="Fern Carpet Path",
        attributes=[
            ("desc",
             "The path leads through the woods along a floor thick with "
             "fern fronds. Insects drone lazily, and a cool draft hints "
             "at a spring somewhere unseen."),
        ],
    )

    rooms["hunters_lookout"] = create_object(
        RoomBase,
        key="Hunters' Lookout",
        attributes=[
            ("desc",
             "A beaten path leads through the woods to a slight rise "
             "used by hunters to watch the game trails. Broken twigs and "
             "old bootprints mark frequent passage."),
        ],
    )

    rooms["tumbled_stones"] = create_object(
        RoomBase,
        key="Tumbled Stones",
        attributes=[
            ("desc",
             "The path leads through the woods past a scatter of tumbled "
             "stones half-sunk in soil. Lichen paints them in gray-green "
             "patches, and small lizards bask when the sun appears."),
        ],
    )

    rooms["thicket_gate"] = create_object(
        RoomBase,
        key="Thicket Gate",
        attributes=[
            ("desc",
             "A narrow path leads through the woods and threads a "
             "natural gate of hawthorn and hazel. The brush tugs at "
             "sleeves, and the air smells green and sharp."),
        ],
    )

    rooms["windbreak_slope"] = create_object(
        RoomBase,
        key="Windbreak Slope",
        attributes=[
            ("desc",
             "The path leads through the woods up a gentle slope where "
             "the trees grow close, muffling the wind. The hush deepens, "
             "broken only by the creak of swaying limbs."),
        ],
    )

    rooms["rolling_rise"] = create_object(
        RoomBase,
        key="Rolling Rise",
        attributes=[
            ("desc",
             "A timeworn path leads through the woods over rolling "
             "ground. The forest thins briefly, offering glimpses of "
             "distant hills between the trunks."),
        ],
    )

    rooms["open_scrub"] = create_object(
        RoomBase,
        key="Open Scrub",
        attributes=[
            ("desc",
             "The path leads through the woods into open scrub where "
             "saplings compete for light. Low shrubs scratch at boots "
             "while the trail threads the brightest ground."),
        ],
    )

    rooms["low_hill_crest"] = create_object(
        RoomBase,
        key="Low Hill Crest",
        attributes=[
            ("desc",
             "The path leads through the woods to a low crest with a "
             "wide view. Grasses mingle with heather and mint, their "
             "scents stirred by a steady breeze."),
        ],
    )

    rooms["scattered_groves"] = create_object(
        RoomBase,
        key="Scattered Groves",
        attributes=[
            ("desc",
             "The path leads through the woods between scattered groves, "
             "where stands of trees break the land into gentle folds. "
             "Bird calls carry far in the thinner canopy."),
        ],
    )

    rooms["wooded_foothills"] = create_object(
        RoomBase,
        key="Wooded Foothills",
        attributes=[
            ("desc",
             "The path leads through the woods onto lightly forested "
             "foothills, where the ground rises and falls in long backs. "
             "Distant ridgelines tease the horizon through breaks in "
             "the trees."),
        ],
    )

    # ── East Gate (zone transition to Ironback Peaks / Cloverfen) ──

    rooms["east_gate"] = create_object(
        RoomGateway,
        key="Eastern Crossroads",
        attributes=[
            ("desc",
             "The wooded path opens onto a windswept crossroads where "
             "the land rises toward distant mountains to the northeast "
             "and gentler rolling plains spread south. A weathered "
             "signpost stands at the fork, its arms pointing toward "
             "civilisation in both directions."),
        ],
    )

    # ── Sawmill spur (north of Edge of Woods) ──────────────────────

    rooms["northern_track"] = create_object(
        RoomBase,
        key="Northern Track",
        attributes=[
            ("desc",
             "A narrower path leads through the woods, trending north "
             "toward the steady rhythm of distant saws. The trail is "
             "lined with woodchips that crunch underfoot."),
        ],
    )

    rooms["sawmill"] = create_object(
        RoomProcessing,
        key="Millholm Sawmill",
        attributes=[
            ("processing_type", "sawmill"),
            ("process_cost", 1),
            ("recipes", [
                {"inputs": {6: 1}, "output": 7, "amount": 1, "cost": 1},
                {"inputs": {40: 1}, "output": 41, "amount": 1, "cost": 3},
            ]),
            ("desc",
             "A packed-earth path leads through the woods into a working "
             "sawmill clearing. Fresh-cut logs are stacked high, and the "
             "scent of sap and sawdust fills the air as blades sing. "
             "Workers feed timber through the great saw while others "
             "stack the finished planks for transport to town."),
        ],
    )

    # ── Smelter spur (south of Edge of Woods) ──────────────────────

    rooms["southern_track"] = create_object(
        RoomBase,
        key="Southern Track",
        attributes=[
            ("desc",
             "A narrower path leads through the woods, trending south "
             "toward the distant glow of banked coals. The air carries "
             "a faint metallic tang and the scent of hot stone."),
        ],
    )

    rooms["smelter"] = create_object(
        RoomProcessing,
        key="Millholm Smelter",
        attributes=[
            ("processing_type", "smelter"),
            ("process_cost", 2),
            ("recipes", [
                # Basic ore → ingot
                {"inputs": {4: 1}, "output": 5, "amount": 1, "cost": 4},
                {"inputs": {23: 1}, "output": 24, "amount": 1, "cost": 2},
                {"inputs": {25: 1}, "output": 26, "amount": 1, "cost": 2},
                {"inputs": {27: 1}, "output": 28, "amount": 1, "cost": 2},
                {"inputs": {30: 1}, "output": 31, "amount": 1, "cost": 5},
                {"inputs": {39: 1}, "output": 38, "amount": 1, "cost": 6},
                # Alloys
                {"inputs": {24: 1, 26: 1}, "output": 32, "amount": 1,
                 "cost": 3},
                {"inputs": {26: 1, 28: 1}, "output": 29, "amount": 1,
                 "cost": 3},
                {"inputs": {5: 1, 36: 1}, "output": 37, "amount": 1,
                 "cost": 5},
            ]),
            ("desc",
             "The path opens into a rough smelting site cut from the "
             "woods. A squat stone furnace radiates heat while charcoal "
             "smolders in stacked pits. Ore carts and tongs lie nearby, "
             "and slag heaps glitter dully under soot. The air shimmers "
             "with heat and the bitter tang of molten metal."),
        ],
    )

    # ── Southern Woods grid (10×6, RoomHarvesting for wood) ─────────
    # resource_count=0 — spawn script sets actual amounts based on
    # economy and demand.

    grid = [[None] * 10 for _ in range(6)]
    for r in range(6):
        for c in range(10):
            name, desc = GRID_ROOMS[r][c]
            grid[r][c] = create_object(
                RoomHarvesting,
                key=name,
                attributes=[
                    ("desc", desc),
                    ("resource_id", 6),
                    ("resource_count", 0),
                    ("abundance_threshold", 5),
                    ("harvest_height", 0),
                    ("harvest_command", "chop"),
                    ("desc_abundant",
                     "Sturdy trees surround you, their trunks thick "
                     "with harvestable wood. There is plenty to fell "
                     "here."),
                    ("desc_scarce",
                     "A few decent trees remain standing among the "
                     "stumps of those already felled."),
                    ("desc_depleted",
                     "Only stumps and saplings remain here. The "
                     "usable timber has been taken."),
                ],
            )

    # ── Replace Trapper's Hut (row 2, col 3) with RoomProcessing ──
    #    Hide (8) → Leather (9)
    grid[2][3].delete()
    grid[2][3] = create_object(
        RoomProcessing,
        key="Trapper's Hut",
        attributes=[
            ("processing_type", "tannery"),
            ("process_cost", 1),
            ("recipes", [
                {"inputs": {8: 1}, "output": 9, "amount": 1, "cost": 1},
                {"inputs": {42: 1}, "output": 43, "amount": 1, "cost": 4},
            ]),
            ("desc",
             "A rough-hewn hut stands among the trees, pelts stretched "
             "to dry on frames. The smell of smoke and tannin lingers "
             "in the air. A crude tanning rack and scraping tools suggest "
             "this is where the local trapper turns raw hides into usable "
             "leather."),
        ],
    )

    # Add details to the replaced Trapper's Hut
    grid[2][3].details = {
        "hut": (
            "The hut is a single room of rough-hewn logs, chinked with "
            "moss and mud. A stone-ringed firepit sits outside the door, "
            "still warm with banked coals. Inside you can glimpse a cot, "
            "a workbench, and bundles of dried herbs hanging from the "
            "low rafters."
        ),
        "pelts": (
            "Half a dozen pelts are stretched on wooden frames — rabbit, "
            "fox, and what might be a young deer. The trapper scrapes and "
            "salts them here before working them into usable leather."
        ),
        "rack": (
            "A crude tanning rack built from lashed branches holds a hide "
            "mid-process, the flesh side scraped clean and dusted with "
            "salt and oak bark. The sharp smell of tannin stings the nose."
        ),
    }

    # ── Add lightweight details to POI grid rooms ─────────────────
    # Players can 'look <keyword>' to inspect these.

    # Row 2 POIs
    grid[1][0].details = {  # Game Trail Crossing
        "trail": (
            "The trails are narrow and well-worn, pressed into the earth by "
            "countless hooves and paws. Deer droppings and the occasional "
            "tuft of fur cling to the low brush on either side."
        ),
        "tracks": (
            "Overlapping prints muddle the soft ground — cloven hooves, "
            "the splayed pads of a fox, and the small neat marks of rabbits."
        ),
    }
    grid[1][2].details = {  # Stone Cairn
        "cairn": (
            "Seven flat stones are stacked with care, each one chosen for "
            "its fit. Moss has claimed the lower layers, but the topmost "
            "stone is clean — someone still tends this marker."
        ),
        "stones": (
            "The stones are river-smoothed and pale gray beneath the moss. "
            "A faint scratching on the second stone might once have been "
            "a rune or a name, but weather has worn it past reading."
        ),
    }
    grid[1][4].details = {  # Fallen Giant
        "trunk": (
            "The trunk is easily four feet across, its bark peeling in long "
            "curls to reveal pale wood riddled with beetle galleries. Shelf "
            "fungi climb its flank in overlapping tiers, and a family of "
            "woodlice scurries from beneath a slab of loose bark."
        ),
        "fungi": (
            "Bracket fungi in muted browns and creams fan out from the "
            "rotting wood. Their undersides are pale and spongy — likely "
            "not poisonous, but not appetising either."
        ),
    }
    grid[1][6].details = {  # Berry Bramble
        "bramble": (
            "Thorny canes arch and tangle in a dense thicket. Dark berries "
            "cluster among the leaves in various stages of ripeness, from "
            "hard green nubs to plump, juice-dark fruit."
        ),
        "berries": (
            "The ripe ones are almost black, bursting at a touch. They "
            "stain fingers purple and taste sharp-sweet. Birds have already "
            "claimed the easiest pickings on the outer branches."
        ),
    }
    grid[1][8].details = {  # Rabbit Warren
        "warren": (
            "Dozens of sandy burrow mouths dot the ground beneath a low "
            "bank, some barely fist-sized, others wide enough for a terrier. "
            "Small droppings litter the entrance area, and the grass is "
            "cropped short in a wide circle around the holes."
        ),
        "burrows": (
            "The burrow entrances are smooth-edged and well-used. Fresh "
            "diggings near the largest hole show the rabbits are still "
            "expanding their underground network."
        ),
    }

    # Row 3 POIs
    grid[2][1].details = {  # Old Snare Line
        "snare": (
            "Rotting cord and bent wire loops dangle from low branches, "
            "long since sprung or gnawed through. The stakes are weathered "
            "gray, driven into the ground at regular intervals — a trapper's "
            "forgotten harvest line."
        ),
        "stakes": (
            "Sharpened stakes of hazel, once fresh-cut, now gray and "
            "splitting. Some lean drunkenly where the soil has softened "
            "with rain. A frayed length of cord still connects two of them."
        ),
    }
    grid[2][5].details = {  # Hollow Log
        "log": (
            "The log is enormous — a toppled oak, long dead, its heartwood "
            "rotted away to leave a tunnel you could almost crawl through. "
            "Inside, the walls are damp and crumbling, home to beetles, "
            "centipedes, and at least one bright orange salamander."
        ),
        "salamander": (
            "A small fire-orange salamander clings to the damp inner wall "
            "of the log, its tiny eyes gleaming. It watches you with the "
            "perfect stillness of something that hopes not to be noticed."
        ),
    }
    grid[2][7].details = {  # Spring-fed Pool
        "pool": (
            "The pool is barely knee-deep and crystal clear. A sandy bottom "
            "is disturbed only where the spring bubbles up, sending tiny "
            "plumes of silt dancing. Water striders dimple the surface, "
            "and a few small fish dart in the shallows."
        ),
        "spring": (
            "The spring rises from a crack in a mossy rock at the pool's "
            "edge, pushing a steady pulse of cold, clean water into the "
            "basin. The water tastes faintly of minerals and stone."
        ),
    }

    # Row 4 POI
    grid[3][1].details = {  # Fox Earth
        "earth": (
            "The main entrance is a dark oval beneath a thick root, just "
            "wide enough for a fox to slip through. Scratch marks score the "
            "packed dirt, and a scattering of small bones — mice, probably — "
            "litters the threshold. A faint, sharp musk rises from the hole."
        ),
        "fur": (
            "Tufts of russet and cream fur snag on the rough bark above "
            "the den entrance. The fox that lives here is well-fed, judging "
            "by the generous thickness of the undercoat."
        ),
        "burrow": (
            "The burrow descends at a shallow angle into darkness. You "
            "can hear faint shuffling from within — the fox is home."
        ),
    }

    # ── Northern Woods row (north of main path) ────────────────
    # Transition zone — denser woods leading to the deep woods.
    # All 10 rooms funnel north into a single entry room.

    northern_woods = []
    for name, desc in NORTHERN_WOODS:
        nw_room = create_object(
            RoomBase,
            key=name,
            attributes=[("desc", desc)],
        )
        northern_woods.append(nw_room)

    # ── Deep Woods Entry (funnel point) ──────────────────────
    # All northern woods rooms converge here. North leads to the
    # procedural deep woods passage; south back to the northern row.

    rooms["deep_woods_entry"] = create_object(
        RoomBase,
        key="Edge of the Deep Woods",
        attributes=[
            ("desc",
             "The trees press close, ancient trunks thick with moss "
             "and tangled undergrowth. Dense thickets of thorn and "
             "briar choke every direction save a narrow gap to the "
             "north, where the forest grows darker still, and the "
             "thinning woods to the south. The air is heavy and "
             "still, and the sounds of the lighter woods seem "
             "muffled and distant."),
        ],
    )
    rooms["deep_woods_entry"].details = {
        "thickets": (
            "Walls of blackthorn and briar, densely woven and "
            "head-high, block every direction but north and south. "
            "Attempting to force a way through would leave you "
            "bloody and no further forward."
        ),
        "gap": (
            "A narrow gap between the thickets opens to the north, "
            "leading into forest so dense and dark it might as well "
            "be night beneath the canopy. The trees beyond are "
            "ancient — far older than anything in the lighter woods."
        ),
    }

    print(f"  Created {len(rooms) + 60 + len(northern_woods)} rooms "
          f"({len(rooms)} named + 60 grid + {len(northern_woods)} "
          f"northern woods).")

    # ══════════════════════════════════════════════════════════════════
    # 2. CREATE EXITS
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # ── Connect to Millholm Town ──────────────────────────────────
    connect_bidirectional_exit(town_rooms["road_far_east"], rooms["forest_path_east"], "east")
    exit_count += 2

    # ── Main path chain (winding east) ─────────────────────────────
    path_connections = [
        ("forest_path_east", "edge_of_woods", "east"),
        ("edge_of_woods", "birch_stand", "northeast"),
        ("birch_stand", "mossy_bend", "east"),
        ("mossy_bend", "creekside_crossing", "southeast"),
        ("creekside_crossing", "tall_canopy", "east"),
        ("tall_canopy", "shadowed_hollow", "east"),
        ("shadowed_hollow", "split_trunk_oak", "northeast"),
        ("split_trunk_oak", "fern_carpet", "east"),
        ("fern_carpet", "hunters_lookout", "southeast"),
        ("hunters_lookout", "tumbled_stones", "east"),
        ("tumbled_stones", "thicket_gate", "northeast"),
        ("thicket_gate", "windbreak_slope", "east"),
        ("windbreak_slope", "rolling_rise", "southeast"),
        ("rolling_rise", "open_scrub", "east"),
        ("open_scrub", "low_hill_crest", "northeast"),
        ("low_hill_crest", "scattered_groves", "east"),
        ("scattered_groves", "wooded_foothills", "east"),
    ]
    for key_a, key_b, direction in path_connections:
        connect_bidirectional_exit(rooms[key_a], rooms[key_b], direction)
        exit_count += 2

    # ── East gate (zone boundary) ─────────────────────────────────
    connect_bidirectional_exit(rooms["wooded_foothills"], rooms["east_gate"], "east")
    exit_count += 2

    # ── Sawmill spur ───────────────────────────────────────────────
    connect_bidirectional_exit(rooms["edge_of_woods"], rooms["northern_track"], "north")
    connect_bidirectional_exit(rooms["northern_track"], rooms["sawmill"], "north")
    exit_count += 4

    # ── Smelter spur ───────────────────────────────────────────────
    connect_bidirectional_exit(rooms["edge_of_woods"], rooms["southern_track"], "south")
    connect_bidirectional_exit(rooms["southern_track"], rooms["smelter"], "south")
    exit_count += 4

    # ── Main path → grid row 1 (10 connections) ───────────────────
    grid_entry_keys = [
        "creekside_crossing", "tall_canopy", "shadowed_hollow",
        "split_trunk_oak", "fern_carpet", "hunters_lookout",
        "tumbled_stones", "thicket_gate", "windbreak_slope",
        "rolling_rise",
    ]
    for col, path_key in enumerate(grid_entry_keys):
        connect_bidirectional_exit(rooms[path_key], grid[0][col], "south")
        exit_count += 2

    # ── Grid east-west connections (bidirectional) ─────────────────
    for r in range(6):
        for c in range(9):
            connect_bidirectional_exit(grid[r][c], grid[r][c + 1], "east")
            exit_count += 2

    # ── Grid north-south connections (bidirectional) ───────────────
    for r in range(5):
        for c in range(10):
            connect_bidirectional_exit(grid[r][c], grid[r + 1][c], "south")
            exit_count += 2

    # ── Grid boundary redirects ─────────────────────────────────────
    # Edge rooms redirect 2 rooms back in the opposite direction,
    # creating a 3-room cycle (A→B→C(edge)→A→B→C→...) so the
    # player sees varied rooms instead of bouncing off a wall.

    # West edge (column 0): going west → column 2 (same row)
    for r in range(6):
        connect_oneway_loopback_exit(
            grid[r][0], "west",
            key="The forest turns you back the way you came.",
            destination=grid[r][2],
        )
        exit_count += 1

    # East edge (column 9): going east → column 7 (same row)
    for r in range(6):
        connect_oneway_loopback_exit(
            grid[r][9], "east",
            key="However you try, you end up where you began.",
            destination=grid[r][7],
        )
        exit_count += 1

    # South edge (row 5): going south → row 3 (same column)
    for c in range(10):
        connect_oneway_loopback_exit(
            grid[5][c], "south",
            key="The woods grow impenetrable further south.",
            destination=grid[3][c],
        )
        exit_count += 1

    # ── Main path → northern woods (bidirectional, 10 pairs) ─────
    for i, path_key in enumerate(grid_entry_keys):
        connect_bidirectional_exit(rooms[path_key], northern_woods[i], "north")
        exit_count += 2

    # ── Northern woods east-west connections ──────────────────────
    for i in range(9):
        connect_bidirectional_exit(northern_woods[i], northern_woods[i + 1], "east")
        exit_count += 2

    # ── Northern woods → deep woods entry (many-to-one, north) ───
    # All 10 rooms funnel north into one entry room. One-way exits
    # only — the single south exit from entry goes to the middle.
    for nw_room in northern_woods:
        exit_obj = create_object(
            ExitVerticalAware,
            key="Edge of the Deep Woods",
            location=nw_room,
            destination=rooms["deep_woods_entry"],
        )
        exit_obj.set_direction("north")
        exit_count += 1

    # ── Deep woods entry → south to middle of northern row ───────
    exit_south = create_object(
        ExitVerticalAware,
        key="Dense Woods",
        location=rooms["deep_woods_entry"],
        destination=northern_woods[4],
    )
    exit_south.set_direction("south")
    exit_count += 1

    print(f"  Created {exit_count} exits.")

    # ══════════════════════════════════════════════════════════════════
    # 3. TAG ROOMS — zone, district, terrain
    # ══════════════════════════════════════════════════════════════════

    all_rooms = list(rooms.values())
    for r in range(6):
        for c in range(10):
            all_rooms.append(grid[r][c])
    all_rooms.extend(northern_woods)

    for room in all_rooms:
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # Terrain — almost everything is FOREST
    for room in all_rooms:
        room.set_terrain(TerrainType.FOREST.value)

    # Sawmill and smelter are indoor/urban structures
    rooms["sawmill"].set_terrain(TerrainType.URBAN.value)
    rooms["smelter"].set_terrain(TerrainType.URBAN.value)

    print("  Tagged all rooms with zone, district, and terrain.")

    # ── Mob area tags ─────────────────────────────────────────────
    # Wolf roaming area: main path rooms (that connect to grid),
    # the 60-room southern grid, and the 10 northern woods rooms.
    # NOT the deep woods entry, sawmill, smelter, or early path rooms.
    wolf_path_keys = [
        "creekside_crossing", "tall_canopy", "shadowed_hollow",
        "split_trunk_oak", "fern_carpet", "hunters_lookout",
        "tumbled_stones", "thicket_gate", "windbreak_slope",
        "rolling_rise",
    ]
    wolf_rooms = [rooms[k] for k in wolf_path_keys]
    for r in range(6):
        for c in range(10):
            wolf_rooms.append(grid[r][c])
    wolf_rooms.extend(northern_woods)
    for room in wolf_rooms:
        room.tags.add("woods_wolves", category="mob_area")
    print(f"  Tagged {len(wolf_rooms)} rooms with mob_area=woods_wolves.")

    # ══════════════════════════════════════════════════════════════════
    # 4. FUTURE CONNECTION NOTES
    # ══════════════════════════════════════════════════════════════════
    # Procedural passages 1 & 2 (entry ↔ clearing) wired in build_game_world.py
    # Procedural passages 3 & 4 (clearing ↔ miners_camp) wired in build_game_world.py
    # Grid POI rooms (Trapper's Hut, Fox Earth) → future mob spawns

    # ── Region map cell tags ────────────────────────────────────────
    # Woods path (north of road): 3 cells covering main path rooms
    _region_tag = "millholm_region"
    _path_keys = [
        "forest_path_east", "edge_of_woods", "birch_stand", "mossy_bend",
        "creekside_crossing", "tall_canopy", "shadowed_hollow",
        "split_trunk_oak", "fern_carpet", "hunters_lookout", "tumbled_stones",
        "thicket_gate", "windbreak_slope", "rolling_rise", "open_scrub",
        "low_hill_crest", "scattered_groves", "wooded_foothills",
    ]
    # Split path into 3 chunks for woods_path_w, woods_path_mid, woods_path_e
    for key in _path_keys[:6]:
        rooms[key].tags.add(f"{_region_tag}:woods_path_w", category="map_cell")
    for key in _path_keys[6:12]:
        rooms[key].tags.add(f"{_region_tag}:woods_path_mid", category="map_cell")
    for key in _path_keys[12:]:
        rooms[key].tags.add(f"{_region_tag}:woods_path_e", category="map_cell")

    # Sawmill and smelter
    rooms["sawmill"].tags.add(f"{_region_tag}:sawmill", category="map_cell")
    rooms["northern_track"].tags.add(f"{_region_tag}:sawmill", category="map_cell")
    rooms["smelter"].tags.add(f"{_region_tag}:smelter", category="map_cell")
    rooms["southern_track"].tags.add(f"{_region_tag}:smelter", category="map_cell")

    # Woods road (main E-W through woods, on the road row)
    rooms["forest_path_east"].tags.add(f"{_region_tag}:woods_road_w", category="map_cell")
    rooms["edge_of_woods"].tags.add(f"{_region_tag}:woods_road_w", category="map_cell")
    for key in _path_keys[4:8]:
        rooms[key].tags.add(f"{_region_tag}:woods_road_mid", category="map_cell")
    for key in _path_keys[8:13]:
        rooms[key].tags.add(f"{_region_tag}:woods_road_e", category="map_cell")
    for key in _path_keys[13:]:
        rooms[key].tags.add(f"{_region_tag}:woods_road_far_e", category="map_cell")

    # Southern woods grid: 10x6 → 9 region cells (3x3 chunks)
    # Chunk mapping: cols 0-2 = west, 3-6 = mid, 7-9 = east
    #                rows 0-1 = north, 2-3 = mid, 4-5 = south
    _grid_chunks = {
        "woods_south_w":  [(r, c) for r in range(0, 2) for c in range(0, 3)],
        "woods_south_mid":[(r, c) for r in range(0, 2) for c in range(3, 7)],
        "woods_south_e":  [(r, c) for r in range(0, 2) for c in range(7, 10)],
        "woods_deep_sw":  [(r, c) for r in range(2, 4) for c in range(0, 3)],
        "tannery":        [(r, c) for r in range(2, 4) for c in range(3, 7)],
        "woods_deep_se":  [(r, c) for r in range(2, 4) for c in range(7, 10)],
        "woods_far_sw":   [(r, c) for r in range(4, 6) for c in range(0, 3)],
        "woods_far_mid":  [(r, c) for r in range(4, 6) for c in range(3, 7)],
        "woods_far_se":   [(r, c) for r in range(4, 6) for c in range(7, 10)],
    }
    for cell_key, positions in _grid_chunks.items():
        for r, c in positions:
            grid[r][c].tags.add(f"{_region_tag}:{cell_key}", category="map_cell")

    # Northern woods → deep woods cells
    for nw_room in northern_woods[:5]:
        nw_room.tags.add(f"{_region_tag}:deep_woods_sw", category="map_cell")
    for nw_room in northern_woods[5:]:
        nw_room.tags.add(f"{_region_tag}:deep_woods_se", category="map_cell")
    rooms["deep_woods_entry"].tags.add(f"{_region_tag}:deep_woods_se", category="map_cell")

    # Woods exit and east gate (zone boundary)
    rooms["wooded_foothills"].tags.add(f"{_region_tag}:woods_exit", category="map_cell")
    rooms["east_gate"].set_terrain(TerrainType.PLAINS.value)
    rooms["east_gate"].tags.add(f"{_region_tag}:east_gate", category="map_cell")

    _region_count = sum(len(v) for v in _grid_chunks.values()) + len(northern_woods) + 30
    print(f"  Tagged ~{_region_count} woods rooms with millholm_region map_cell tags.")

    print("  Millholm Woods complete.\n")
    return rooms

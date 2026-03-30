"""
Millholm Farms — the agricultural district west of Millholm Town.

Builds ~67 rooms including:
- The Old Trade Way (10 road segments, continuing west from town)
- Goldwheat Farm (homestead, garden, 7x3 wheat/fence/track grid)
- South Fork road (4 rooms, connecting to Abandoned Farm)
- Brightwater Cotton Farm (farmyard, cotton barn, 3x3 cotton field grid,
  underground tunnel network)
- Abandoned Farm (ruined buildings, 4x2 overgrown field grid)
- Millholm Windmill (RoomProcessing — wheat to flour)

Goldwheat wheat fields are RoomHarvesting (resource_id=1, harvest command).
Cotton fields are RoomHarvesting (resource_id=10, pick command).

Usage:
    from world.game_world.millholm_farms import build_millholm_farms
    build_millholm_farms(town_rooms)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from typeclasses.terrain.rooms.room_processing import RoomProcessing
from typeclasses.world_objects.chest import WorldChest
from typeclasses.world_objects.key_item import KeyItem
from utils.exit_helpers import connect, connect_door


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_farms"


def build_millholm_farms(town_rooms):
    """
    Build the Millholm Farms district.

    Args:
        town_rooms: Dict of room objects from build_millholm_town().
                    Needs town_rooms["road_far_west"] as connection point.
    """

    rooms = {}

    # ══════════════════════════════════════════════════════════════════
    # 1. CREATE ROOMS
    # ══════════════════════════════════════════════════════════════════

    # ── The Old Trade Way — road west from town (10 segments) ──────

    rooms["farm_road_1"] = create_object(
        RoomBase,
        key="Old Trade Lane",
        attributes=[
            ("desc",
             "The cobblestones give way to hard-packed earth as the trade road "
             "leaves Millholm behind. Dry-stone walls line both sides, marking "
             "the boundaries of the first farmsteads. Cart ruts are worn deep "
             "into the road from generations of harvest wagons."),
        ],
    )

    rooms["farm_road_2"] = create_object(
        RoomBase,
        key="Old Trade Lane",
        attributes=[
            ("desc",
             "Rolling farmland stretches away on both sides of the road. "
             "Patchwork fields of green and gold create a quilt-like pattern "
             "across the gentle hills. The air smells of turned earth and "
             "growing things, and the distant lowing of cattle drifts on "
             "the breeze."),
        ],
    )

    rooms["farm_road_meadow"] = create_object(
        RoomBase,
        key="Old Trade Lane",
        attributes=[
            ("desc",
             "The road curves gently around a wildflower meadow where bees "
             "drone lazily among the blossoms. A wooden bench has been placed "
             "here beneath a spreading hawthorn tree, offering rest to weary "
             "travelers. Butterflies dance above the tall grass."),
        ],
    )

    rooms["farm_road_oak"] = create_object(
        RoomBase,
        key="Old Trade Lane",
        attributes=[
            ("desc",
             "A massive old oak tree stands at a crossing point on the road, "
             "its trunk wider than a cart. A worn path leads north toward "
             "farmland, marked by a weathered sign reading 'Goldwheat Farm'. "
             "Acorns crunch underfoot and squirrels chatter from the branches "
             "above."),
        ],
    )

    rooms["farm_road_hill"] = create_object(
        RoomBase,
        key="Old Trade Lane",
        attributes=[
            ("desc",
             "The road climbs a gentle rise here, offering a commanding view "
             "of the surrounding farmland. To the east, Millholm's rooftops "
             "are visible above the treeline. Westward, more farms dot the "
             "landscape, their fields stretching to the horizon."),
        ],
    )

    rooms["farm_road_crossroads"] = create_object(
        RoomBase,
        key="Old Trade Lane",
        attributes=[
            ("desc",
             "A crossroads where a south-running track branches off the main "
             "road. The southern path is narrower and less traveled, winding "
             "between hedgerows toward distant homesteads."),
        ],
    )

    rooms["farm_road_west"] = create_object(
        RoomBase,
        key="Dirt Track",
        attributes=[
            ("desc",
             "Two muddy wagon ruts carve through the grass, the only "
             "evidence that this is a road at all. Weeds push up between "
             "the ruts and the hedgerows on either side are slowly "
             "narrowing the gap. Only the regular passage of a farmer's "
             "cart keeps this track from disappearing entirely. A "
             "lopsided scarecrow watches over a nearby field, its "
             "tattered clothes flapping in the wind."),
        ],
    )

    rooms["farm_road_cotton"] = create_object(
        RoomBase,
        key="Dirt Track",
        attributes=[
            ("desc",
             "The dirt track narrows further here, the twin wagon ruts "
             "almost lost in the mud. Cotton fields stretch away to the "
             "north, their white bolls bright against the dark earth. A "
             "path branches north toward a cluster of farm buildings — "
             "the Brightwater Cotton Farm. Thistles and dock leaves "
             "crowd the edges of the track."),
        ],
    )

    rooms["farm_road_mill"] = create_object(
        RoomBase,
        key="Dirt Track",
        attributes=[
            ("desc",
             "The wagon ruts deepen where they curve toward the old "
             "windmill, churned to thick mud by the regular passage of "
             "grain carts. The great wooden sails turn lazily in the "
             "breeze, and the rhythmic grinding of millstones can be "
             "heard from within. Sacks of grain are stacked by the "
             "trackside awaiting collection. Beyond the mill, the track "
             "fades into open farmland."),
        ],
    )

    # ── Millholm Windmill (RoomProcessing — wheat → flour) ────────
    rooms["windmill"] = create_object(
        RoomProcessing,
        key="Millholm Windmill",
        attributes=[
            ("processing_type", "windmill"),
            ("process_cost", 1),
            ("recipes", [
                {"inputs": {1: 1}, "output": 2, "amount": 1, "cost": 1},
            ]),
            ("desc",
             "The interior of the old stone windmill is filled with the "
             "rumble and clatter of heavy millstones grinding wheat into "
             "flour. A thick coating of white dust covers every surface, "
             "and the air is hazy with flour particles that dance in the "
             "shafts of light from narrow windows. Great wooden gears turn "
             "overhead, connected by thick shafts to the sails outside. "
             "Sacks of wheat wait to be processed, while finished flour "
             "is packed into barrels for transport to town."),
        ],
    )

    # ── Weaving House spur (south of farm_road_meadow) ─────────────

    rooms["weavers_track"] = create_object(
        RoomBase,
        key="Weaver's Track",
        attributes=[
            ("desc",
             "A well-trodden path leads south from the road through a gap "
             "in the hedgerow. The sound of rhythmic clacking drifts from "
             "a low stone building ahead, its chimney trailing a thin wisp "
             "of smoke. Cotton fluff clings to the bushes along the path "
             "like unseasonable snow."),
        ],
    )

    rooms["weaving_house"] = create_object(
        RoomProcessing,
        key="Millholm Weaving House",
        attributes=[
            ("processing_type", "loom"),
            ("process_cost", 1),
            ("recipes", [
                {"inputs": {10: 1}, "output": 11, "amount": 1, "cost": 1},
            ]),
            ("desc",
             "The low-ceilinged stone building houses three heavy wooden "
             "looms, their frames darkened with age and oil. Spindles of "
             "raw cotton thread hang from racks along the walls, and bolts "
             "of finished cloth in natural cream and undyed grey are stacked "
             "on shelves near the door. The steady clack-clack of shuttles "
             "fills the room, and the air is thick with floating fibres "
             "that catch the light from deep-set windows."),
            ("details", {
                "loom": (
                    "A heavy wooden frame strung with taut warp threads. "
                    "The weaver throws the shuttle back and forth, each pass "
                    "adding another weft thread to the growing cloth. The "
                    "mechanism is simple but the skill is in the tension — "
                    "too tight and the cloth bunches, too loose and it falls "
                    "apart."
                ),
                "cloth": (
                    "Bolts of finished cloth in natural cream and undyed "
                    "grey. The weave is tight and even — good workmanship "
                    "for a village operation."
                ),
            }),
        ],
    )

    # ── South Fork (4 rooms, branching south from crossroads) ──────

    rooms["south_fork_1"] = create_object(
        RoomBase,
        key="South Fork",
        attributes=[
            ("desc",
             "This narrow track winds south through hedgerows and low stone "
             "walls. The path is less maintained than the main road — weeds "
             "push through the packed earth, and overhanging branches form "
             "a patchy canopy. Muddy hoofprints suggest livestock are driven "
             "this way regularly."),
        ],
    )

    rooms["south_fork_2"] = create_object(
        RoomBase,
        key="South Fork",
        attributes=[
            ("desc",
             "The track descends into a shallow valley where the ground "
             "turns soft and muddy. Puddles fill the deeper ruts, and the "
             "hedgerows give way to tangled blackberry brambles. A broken "
             "fence gate hangs open to the east, and the smell of damp "
             "earth is heavy in the air."),
        ],
    )

    rooms["south_fork_3"] = create_object(
        RoomBase,
        key="South Fork",
        attributes=[
            ("desc",
             "The path reaches a particularly overgrown stretch where an "
             "eastward trail branches off through a gap in the hedgerow. "
             "The eastern track is almost hidden by brambles and nettles, "
             "as if whoever once maintained it stopped caring long ago. "
             "A rusted sign lies face-down in the weeds."),
        ],
    )

    rooms["south_fork_end"] = create_object(
        RoomBase,
        key="South Fork",
        attributes=[
            ("desc",
             "The track peters out at a muddy clearing surrounded by dense "
             "hedgerow. A collapsed wooden structure — perhaps once a "
             "livestock pen — lies in a heap of rotting timber. There is "
             "nothing further south but wild countryside. A faint trail "
             "through the undergrowth suggests someone still comes this "
             "way occasionally."),
        ],
    )

    # ── Brightwater Cotton Farm (14 surface rooms) ─────────────────

    rooms["bw_track"] = create_object(
        RoomBase,
        key="Brightwater Farm - Dirt Track",
        attributes=[
            ("desc",
             "A rutted dirt track leads north from the trade road toward "
             "the Brightwater Cotton Farm. Rows of young cotton plants line "
             "both sides of the path, their leaves rustling softly. "
             "Halfling-sized boot prints are pressed into the soft earth."),
        ],
    )

    rooms["bw_yard"] = create_object(
        RoomBase,
        key="Brightwater Farm - Yard",
        attributes=[
            ("desc",
             "The central farmyard of Brightwater Farm is a busy hub of "
             "activity. A well-maintained halfling farmhouse sits to the "
             "west, its chimney trailing wood smoke. Cotton-laden carts "
             "wait to be unloaded, and canvas sacks of raw cotton bolls "
             "are stacked against the farmhouse wall. Chickens scratch "
             "in the packed earth around a stone water trough."),
        ],
    )

    rooms["bw_barn"] = create_object(
        RoomBase,
        key="Brightwater Farm - Cotton Barn",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "This spacious wooden barn is dedicated to processing and "
             "storing the farm's cotton harvest. Bales of raw cotton are "
             "stacked high along the walls, while wooden gins and carding "
             "frames occupy the center floor. The air is thick with cotton "
             "fibers that drift like snow in the light from high windows. "
             "Halfling workers sort the harvest by quality, their small "
             "hands deft and practiced."),
        ],
    )

    rooms["bw_shed"] = create_object(
        RoomBase,
        key="Brightwater Farm - Drying Shed",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Long wooden racks fill this open-sided shed, draped with "
             "cotton that has been washed and spread to dry. The shed is "
             "positioned to catch the prevailing breeze, and the white "
             "cotton billows gently like clouds brought to earth. Bundles "
             "of dried cotton fiber, ready for spinning, are packed into "
             "baskets along one wall."),
        ],
    )

    rooms["bw_well"] = create_object(
        RoomBase,
        key="Brightwater Farm - Well",
        attributes=[
            ("desc",
             "A deep stone well stands at the edge of the cotton fields, "
             "its bucket and winch well-oiled and maintained. The water "
             "here is cold and clear, drawn from an underground spring "
             "that also feeds the irrigation channels running between the "
             "cotton rows. Watering cans and buckets are stacked nearby "
             "for the field workers."),
            ("details", {
                "well": (
                    "The well is built from neatly fitted fieldstone, about "
                    "three feet high with a wooden crossbeam and iron winch. "
                    "The rope is thick hemp, recently replaced. Peering over "
                    "the edge you can see dark water glinting far below."
                ),
                "bucket": (
                    "A sturdy oak bucket hangs from the winch chain, damp "
                    "from recent use."
                ),
                "water": (
                    "The water is crystal clear and ice cold — fed by a deep "
                    "underground spring."
                ),
            }),
        ],
    )

    rooms["bw_farmhouse"] = create_object(
        RoomBase,
        key="Brightwater Farm - Farmhouse",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A cosy halfling farmhouse with low ceilings and warm "
             "plaster walls. Dried cotton stalks hang in bundles from "
             "the rafters, and a stone hearth dominates one wall, a "
             "kettle hanging over glowing coals. A sturdy kitchen table "
             "is covered with ledgers, seed catalogues, and a half-eaten "
             "loaf of bread. Through the small round windows, the cotton "
             "fields stretch away in every direction."),
        ],
    )

    # ── Brightwater Cotton Fields (3×3 grid) ───────────────────────

    # All cotton fields are RoomHarvesting for cotton (resource_id=10)
    _cotton_attrs = [
        ("resource_id", 10),
        ("resource_count", 0),
        ("abundance_threshold", 4),
        ("harvest_height", 0),
        ("harvest_command", "pick"),
        ("desc_abundant",
         "The cotton plants are heavy with ripe bolls, white puffs "
         "bursting from their casings. There is plenty to pick here."),
        ("desc_scarce",
         "Many of the cotton plants have already been picked, though "
         "a few ripe bolls remain on scattered stalks."),
        ("desc_depleted",
         "The cotton plants have been thoroughly picked. Only bare "
         "stalks and empty casings remain."),
    ]

    rooms["bw_field_nw"] = create_object(
        RoomHarvesting,
        key="Cotton Field - Northwest",
        attributes=_cotton_attrs + [
            ("desc",
             "Neat rows of cotton plants stretch in every direction, their "
             "dark green leaves sheltering clusters of white cotton bolls. "
             "The plants reach waist-height on a human — chest-height on "
             "the halflings who tend them. The rich, dark soil is carefully "
             "weeded and irrigated."),
        ],
    )

    rooms["bw_field_n"] = create_object(
        RoomHarvesting,
        key="Cotton Field - North",
        attributes=_cotton_attrs + [
            ("desc",
             "The northern stretch of cotton fields runs up against a "
             "low stone wall marking the farm boundary. Beyond the wall, "
             "wild meadow grass grows tall. The cotton here is thick and "
             "healthy, the bolls fat and ready for picking. A halfling's "
             "wide-brimmed hat sits forgotten on a fence post."),
        ],
    )

    rooms["bw_field_ne"] = create_object(
        RoomHarvesting,
        key="Cotton Field - Northeast",
        attributes=_cotton_attrs + [
            ("desc",
             "The northeastern corner of the cotton fields borders a "
             "small copse of birch trees. Cotton plants grow right up to "
             "the treeline, their white bolls a striking contrast against "
             "the silver bark. Birdsong fills the air from the sheltering "
             "branches."),
        ],
    )

    rooms["bw_field_w"] = create_object(
        RoomHarvesting,
        key="Cotton Field - West",
        attributes=_cotton_attrs + [
            ("desc",
             "The western cotton fields slope gently downhill toward a "
             "small stream that provides natural irrigation. The cotton "
             "plants here are particularly lush, benefiting from the extra "
             "moisture. Dragonflies hover over the irrigation channels "
             "between the rows."),
        ],
    )

    rooms["bw_field_center"] = create_object(
        RoomHarvesting,
        key="Cotton Field - Central",
        attributes=_cotton_attrs + [
            ("desc",
             "Standing in the heart of the cotton fields, the white-topped "
             "plants stretch away in every direction like a sea of clouds. "
             "The farm buildings are barely visible to the south, and the "
             "only sounds are the rustle of leaves and the drone of insects. "
             "It would be easy to lose oneself out here."),
        ],
    )

    rooms["bw_field_e"] = create_object(
        RoomHarvesting,
        key="Cotton Field - East",
        attributes=_cotton_attrs + [
            ("desc",
             "The eastern cotton field runs alongside a wooden fence that "
             "separates it from a fallow field being rested for next season. "
             "The contrast between the thriving cotton and the empty brown "
             "earth is stark. Crows patrol the fence posts, watching for "
             "insects disturbed by the field workers."),
        ],
    )

    rooms["bw_field_sw"] = create_object(
        RoomHarvesting,
        key="Cotton Field - Southwest",
        attributes=_cotton_attrs + [
            ("desc",
             "The southwestern corner of the fields is closest to the "
             "farmyard. Halfling children chase each other between the "
             "cotton rows, their laughter carrying on the wind. A canvas "
             "awning has been set up here where workers take their midday "
             "rest, with clay jugs of water and bundles of bread."),
        ],
    )

    rooms["bw_field_s"] = create_object(
        RoomHarvesting,
        key="Cotton Field - South",
        attributes=_cotton_attrs + [
            ("desc",
             "The southern edge of the cotton fields borders the farmyard. "
             "A wooden gate in the fence allows easy access between the "
             "working areas and the fields. Baskets of freshly picked "
             "cotton bolls sit at the end of each row, waiting to be "
             "carried to the barn for processing."),
        ],
    )

    rooms["bw_field_se"] = create_object(
        RoomHarvesting,
        key="Cotton Field - Southeast",
        attributes=_cotton_attrs + [
            ("desc",
             "The southeastern cotton field is the newest planting, with "
             "younger, shorter plants that haven't yet produced bolls. "
             "Halfling farmers move carefully between the rows, weeding "
             "and checking for pests. Stakes and twine mark out sections "
             "where different cotton varieties are being trialed."),
        ],
    )

    # ── Brightwater Underground (4 rooms) ──────────────────────────

    rooms["bw_cellar"] = create_object(
        RoomBase,
        key="Brightwater Farm - Root Cellar",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A cool underground chamber beneath the cotton barn, lined "
             "with rough stone shelves holding jars of preserves, root "
             "vegetables, and cured meats. The halflings clearly live "
             "well. A suspicious draught from the south wall suggests "
             "there may be more to this cellar than meets the eye."),
        ],
    )

    rooms["bw_tunnel"] = create_object(
        RoomBase,
        key="Underground Passage",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A narrow tunnel carved through clay and soft stone, shored "
             "up with halfling-sized timber frames. The ceiling is low — "
             "comfortable for a halfling, cramped for anyone taller. "
             "The passage is well-worn, suggesting regular use. Small "
             "oil lamps in wall niches provide dim, flickering light."),
        ],
    )

    rooms["bw_chamber"] = create_object(
        RoomBase,
        key="Hidden Chamber",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A small, secret chamber at the end of the tunnel. Wooden "
             "chests and locked strongboxes line the walls — the "
             "Brightwaters' private vault. A ledger on a small desk "
             "records transactions in neat halfling script. Whatever "
             "the Brightwaters are storing here, they clearly don't "
             "want it found."),
        ],
    )

    rooms["bw_exit"] = create_object(
        RoomBase,
        key="Tunnel Exit",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "The tunnel ends at a concealed exit disguised as a rabbit "
             "hole in a grassy bank. Roots dangle from the low ceiling, "
             "and daylight filters in from above. The exit is cleverly "
             "hidden — from outside, it would be nearly impossible to "
             "spot among the brambles and undergrowth."),
        ],
    )

    # ── Goldwheat Farm (24 rooms) ────────────────────────────────
    #
    #                     Homestead
    #                         |
    #                       Garden
    #                       (gate)
    # wheat wheat fence  track  fence wheat wheat   (north row)
    #   |     |     |      |      |     |     |
    # wheat wheat fence  track  fence wheat wheat   (middle row)
    #   |     |     |      |      |     |     |
    # wheat wheat fence  track  fence wheat wheat   (south row)
    #                         |
    #                       Lane
    #                         |
    #                   (Old Trade Way)

    _wheat_attrs = [
        ("resource_id", 1),
        ("resource_count", 0),
        ("abundance_threshold", 4),
        ("harvest_height", 0),
        ("harvest_command", "harvest"),
        ("desc_abundant",
         "Golden wheat grows tall and thick here, the heavy heads of "
         "grain swaying gently in the breeze. The stalks are chest-high "
         "and dense, ready for harvesting. The rich smell of ripe grain "
         "fills the air."),
        ("desc_scarce",
         "Patches of harvested stubble break up the remaining wheat. "
         "Some good stalks still stand in scattered clumps, though the "
         "best grain has already been taken."),
        ("desc_depleted",
         "This section has been thoroughly harvested, leaving only short "
         "stubble and scattered chaff. The bare earth shows between the "
         "rows of cut stalks."),
        ("desc",
         "Golden wheat grows tall and thick here, the heavy heads of "
         "grain swaying gently in the breeze. The stalks are chest-high "
         "and dense, ready for harvesting. The rich smell of ripe grain "
         "fills the air."),
    ]

    rooms["gw_homestead"] = create_object(
        RoomBase,
        key="Goldwheat Farm - Homestead",
        attributes=[
            ("desc",
             "The Goldwheat homestead is a sturdy stone-and-timber "
             "farmhouse with a steep thatched roof. Smoke curls lazily "
             "from the chimney, and warm lamplight spills from small "
             "windows. A large threshing floor occupies the yard, and "
             "farming tools lean against the walls. The smell of fresh-"
             "baked bread drifts from within."),
        ],
    )

    rooms["gw_garden"] = create_object(
        RoomHarvesting,
        key="Goldwheat Farm - Garden",
        attributes=[
            ("desc",
             "A well-tended kitchen garden sits behind the farmhouse, "
             "bursting with vegetables and herbs. Neat rows of beans, "
             "squash, and root vegetables grow alongside fragrant rosemary, "
             "thyme, and lavender. Silvery-green sage bushes grow in a "
             "sunny patch by the stone wall, their leaves aromatic and "
             "plentiful. A low stone wall and a sturdy wooden gate "
             "separate the garden from the wheat fields to the south."),
            ("resource_id", 18),           # Sage Leaf
            ("resource_count", 0),         # spawn script sets amount
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "gather"),
            ("desc_abundant",
             "Silvery-green sage bushes grow in thick clumps by the "
             "stone wall. There are plenty of sage leaves to gather."),
            ("desc_scarce",
             "The sage bushes have been picked over — only a few small "
             "leaves remain on the stems."),
            ("desc_depleted",
             "The sage bushes have been stripped bare. Give them time "
             "to grow back."),
        ],
    )

    rooms["gw_barn"] = create_object(
        RoomBase,
        key="Goldwheat Farm - Barn",
        attributes=[
            ("desc",
             "A large timber barn with a high, vaulted roof. Bales of "
             "harvested wheat are stacked along the walls, and farming "
             "equipment — scythes, rakes, and sickles — hangs from "
             "wooden pegs. A heavy cart sits in the center, half-loaded "
             "with grain sacks destined for the windmill. Dust motes "
             "drift in the shafts of light that filter through gaps "
             "in the plank walls. The air smells of dry straw and earth."),
        ],
    )

    rooms["gw_lane"] = create_object(
        RoomBase,
        key="Goldwheat Farm - Lane",
        attributes=[
            ("desc",
             "A well-trodden farm lane leads north from the trade road "
             "toward the Goldwheat homestead. Tall hedgerows line both "
             "sides, and the golden tips of wheat are visible over the "
             "tops. Wagon wheel tracks are worn deep into the earth."),
        ],
    )

    # 7x3 grid — cols: wheat, wheat, fence, track, fence, wheat, wheat
    _gw_col_info = [
        (RoomHarvesting, "Wheat Field", _wheat_attrs),
        (RoomHarvesting, "Wheat Field", _wheat_attrs),
        (RoomBase, "Goldwheat Farm - West Fenceline",
         [("desc",
           "The western fenceline runs alongside the farm track. "
           "Sturdy wooden rails separate the well-worn path from the "
           "wheat fields beyond. The fence posts are weathered grey, "
           "and a few have been scratched by passing cart axles. Golden "
           "wheat presses against the rails to the west.")]),
        (RoomBase, "Goldwheat Farm - Track",
         [("desc",
           "A well-worn dirt track runs between the wheat fields, "
           "separated from the grain by sturdy wooden fences on either "
           "side. Wagon ruts are worn deep into the packed earth from "
           "years of harvest loads. The golden wheat rises above the "
           "fence rails on both sides.")]),
        (RoomBase, "Goldwheat Farm - East Fenceline",
         [("desc",
           "The eastern fenceline mirrors its western counterpart, "
           "marking the boundary between the farm track and the wheat "
           "fields. A scarecrow stands nearby, straw hat askew, keeping "
           "watch over the grain. Through the rails, thick wheat rows "
           "stretch away to the east.")]),
        (RoomHarvesting, "Wheat Field", _wheat_attrs),
        (RoomHarvesting, "Wheat Field", _wheat_attrs),
    ]

    gw_grid = []  # gw_grid[row][col], row 0=south, 2=north
    for row in range(3):
        grid_row = []
        for col, (tc, name, attrs) in enumerate(_gw_col_info):
            room = create_object(tc, key=name, attributes=list(attrs))
            rooms[f"gw_r{row}_c{col}"] = room
            grid_row.append(room)
        gw_grid.append(grid_row)

    # ── Abandoned Farm (11 rooms) ──────────────────────────────────

    rooms["ab_path"] = create_object(
        RoomBase,
        key="Overgrown Path",
        attributes=[
            ("desc",
             "A barely visible path pushes east through thick brambles "
             "and nettles. The vegetation has reclaimed most of the track, "
             "leaving only a narrow gap where someone has recently forced "
             "their way through. Broken spider webs and bent branches "
             "suggest this path sees occasional traffic despite its "
             "abandoned appearance."),
        ],
    )

    rooms["ab_yard"] = create_object(
        RoomBase,
        key="Abandoned Farmyard",
        attributes=[
            ("desc",
             "The remains of a once-prosperous farmstead lie in sad "
             "disrepair. A collapsed farmhouse leans drunkenly to one "
             "side, its roof caved in and walls green with moss. Weeds "
             "and saplings have pushed through the cobblestones of what "
             "was once a tidy yard. A rusted plough sits forgotten in the "
             "corner, slowly being consumed by ivy."),
        ],
    )

    rooms["ab_barn"] = create_object(
        RoomBase,
        key="Ruined Barn",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "The skeleton of a large barn stands open to the sky, its "
             "roof long since collapsed. Massive oak beams jut at angles "
             "from the remaining walls, and piles of rotting hay moulder "
             "in the corners. Birds nest in the rafters, and small animals "
             "have made homes in the debris. Despite the decay, the stone "
             "foundation remains solid."),
        ],
    )

    rooms["ab_field_1"] = create_object(
        RoomBase,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "What was once a cultivated field has been reclaimed by "
             "nature. Tall grass, thistles, and wild herbs grow waist-high "
             "in a tangled mass. The ghost lines of old furrows are still "
             "visible beneath the wild growth, running in disciplined "
             "rows that nature is slowly erasing."),
        ],
    )

    rooms["ab_field_2"] = create_object(
        RoomBase,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "Wild flowers have colonized this abandoned field in a riot "
             "of color. Poppies, cornflowers, and daisies nod in the "
             "breeze among the tall weeds. Bees and butterflies move "
             "busily from bloom to bloom. Whatever crops once grew here "
             "have long been displaced."),
        ],
    )

    rooms["ab_field_3"] = create_object(
        RoomHarvesting,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "Thick brambles and blackberry canes have taken hold in this "
             "corner of the abandoned farm, forming impenetrable thickets. "
             "Among them, a more sinister plant has flourished — vipervine, "
             "its dark green tendrils coiling through the brambles like "
             "slow-moving serpents. The vine's thorns are longer and sharper "
             "than the blackberries', and its leaves have a faintly oily "
             "sheen. It has grown completely out of control here, "
             "strangling the fence posts and pulling down what remains "
             "of the boundary wall."),
            ("resource_id", 20),           # Vipervine
            ("resource_count", 0),         # spawn script sets amount
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "gather"),
            ("desc_abundant",
             "Vipervine coils through the brambles in thick, dark ropes. "
             "There is plenty to gather — if you don't mind the thorns."),
            ("desc_scarce",
             "Most of the vipervine has been cut back. A few thin tendrils "
             "still cling to the fence posts."),
            ("desc_depleted",
             "The vipervine has been stripped clean. Only blackberry "
             "canes and bare thorns remain."),
        ],
    )

    rooms["ab_field_4"] = create_object(
        RoomBase,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "The remnants of an old orchard struggle on in this section "
             "of the abandoned farm. Gnarled apple trees, unpruned for "
             "years, still bear small, wormy fruit. Their twisted branches "
             "create eerie shapes against the sky, and fallen apples "
             "rot in the long grass below."),
        ],
    )

    rooms["ab_field_5"] = create_object(
        RoomBase,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "A tumbled stone wall cuts through this overgrown field, "
             "once dividing crop sections but now just another obstacle "
             "in the wilderness. Moss and lichen cover every stone, and "
             "ferns grow from the gaps. A fox has dug its den beneath "
             "the largest section of remaining wall."),
        ],
    )

    rooms["ab_field_6"] = create_object(
        RoomBase,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "The field here slopes down toward a boggy depression where "
             "water has collected. Reeds and rushes grow thick around the "
             "marshy patch, and the ground squelches underfoot. Frogs "
             "croak from hidden pools, and dragonflies dart over the "
             "stagnant water."),
        ],
    )

    rooms["ab_field_7"] = create_object(
        RoomBase,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "A collapsed scarecrow lies face-down in the weeds, its "
             "wooden frame rotting and its clothes reduced to rags. The "
             "field around it has gone entirely to seed — whatever grain "
             "once grew here has been replaced by wild oats, dandelions, "
             "and dock leaves. Crows sit on the nearest fence post, "
             "clearly unimpressed by the fallen sentinel."),
        ],
    )

    rooms["ab_field_8"] = create_object(
        RoomBase,
        key="Overgrown Field",
        attributes=[
            ("desc",
             "The furthest corner of the abandoned farm borders wild "
             "woodland. Young saplings are advancing from the treeline, "
             "slowly reclaiming the field for the forest. In a few more "
             "years, there will be no sign that crops ever grew here. "
             "The transition from farm to forest is gradual and strangely "
             "beautiful."),
        ],
    )

    print(f"  Created {len(rooms)} rooms.")

    # ══════════════════════════════════════════════════════════════════
    # 2. CREATE EXITS
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # ── Connect to Millholm Town ──────────────────────────────────
    connect(town_rooms["road_far_west"], rooms["farm_road_1"], "west")
    exit_count += 2

    # ── Main road chain (east to west) ─────────────────────────────
    road_chain = [
        "farm_road_1", "farm_road_2", "farm_road_meadow",
        "farm_road_oak", "farm_road_hill", "farm_road_crossroads",
        "farm_road_west", "farm_road_cotton", "farm_road_mill",
    ]
    for i in range(len(road_chain) - 1):
        connect(rooms[road_chain[i]], rooms[road_chain[i + 1]], "west")
        exit_count += 2

    # Road end → Windmill (enter the building)
    connect(rooms["farm_road_mill"], rooms["windmill"], "west")
    exit_count += 2

    # ── Weaving House spur (south of meadow) ─────────────────────
    connect(rooms["farm_road_meadow"], rooms["weavers_track"], "south")
    connect(rooms["weavers_track"], rooms["weaving_house"], "south")
    exit_count += 4

    # ── South Fork (branching south from crossroads) ───────────────
    connect(rooms["farm_road_crossroads"], rooms["south_fork_1"], "south")
    connect(rooms["south_fork_1"], rooms["south_fork_2"], "south")
    connect(rooms["south_fork_2"], rooms["south_fork_3"], "south")
    connect(rooms["south_fork_3"], rooms["south_fork_end"], "south")
    exit_count += 8

    # ── South Fork → Abandoned Farm ────────────────────────────────
    connect(rooms["south_fork_3"], rooms["ab_path"], "east")
    exit_count += 2

    # ── Goldwheat Farm ─────────────────────────────────────────────
    connect(rooms["farm_road_oak"], rooms["gw_lane"], "north")
    connect(rooms["gw_lane"], gw_grid[0][3], "north")
    exit_count += 4

    # Grid: horizontal connections (east-west)
    for row in range(3):
        for col in range(6):
            connect(gw_grid[row][col], gw_grid[row][col + 1], "east")
    exit_count += 36

    # Grid: vertical connections (north-south)
    for col in range(7):
        for row in range(2):
            connect(gw_grid[row][col], gw_grid[row + 1][col], "north")
    exit_count += 28

    # North track → garden (openable gate)
    gate_ab, gate_ba = connect_door(
        gw_grid[2][3], rooms["gw_garden"], "north",
        key="a wooden farm gate",
        closed_ab=(
            "A sturdy wooden gate blocks the path north into the "
            "farmhouse garden. The gate is latched but not locked."
        ),
        open_ab=(
            "The farm gate stands open, revealing a well-tended "
            "kitchen garden beyond."
        ),
        closed_ba=(
            "A sturdy wooden gate blocks the path south onto the "
            "farm track between the wheat fields."
        ),
        open_ba=(
            "The farm gate stands open, the farm track stretching "
            "south between fenced wheat fields."
        ),
        door_name="gate",
    )
    exit_count += 2

    # Garden → homestead
    connect(rooms["gw_garden"], rooms["gw_homestead"], "north")
    exit_count += 2

    # North-east wheat → barn (barn doors)
    connect_door(
        gw_grid[2][6], rooms["gw_barn"], "north",
        key="a pair of barn doors",
        closed_ab=(
            "A pair of tall wooden barn doors are shut tight, their "
            "iron hinges dark with age."
        ),
        open_ab=(
            "The barn doors stand wide open, revealing the dim "
            "interior of the Goldwheat barn beyond."
        ),
        closed_ba=(
            "The barn doors are closed, blocking the way south "
            "into the wheat fields."
        ),
        open_ba=(
            "The barn doors stand open. Golden wheat fields "
            "stretch away to the south."
        ),
        door_name="doors",
    )
    exit_count += 2

    # ── Brightwater Cotton Farm (branching north from cotton road) ──
    connect(rooms["farm_road_cotton"], rooms["bw_track"], "north")
    connect(rooms["bw_track"], rooms["bw_yard"], "north")
    exit_count += 4

    # Yard → farm buildings
    connect(rooms["bw_yard"], rooms["bw_barn"], "west")
    connect(rooms["bw_yard"], rooms["bw_shed"], "east")
    connect(rooms["bw_yard"], rooms["bw_well"], "north")
    connect(rooms["bw_yard"], rooms["bw_farmhouse"], "northwest")
    exit_count += 8

    # Well → cotton field grid (south entrance)
    connect(rooms["bw_well"], rooms["bw_field_s"], "north")
    exit_count += 2

    # Cotton field 3×3 grid connections
    # Top row (east-west)
    connect(rooms["bw_field_nw"], rooms["bw_field_n"], "east")
    connect(rooms["bw_field_n"], rooms["bw_field_ne"], "east")
    # Middle row (east-west)
    connect(rooms["bw_field_w"], rooms["bw_field_center"], "east")
    connect(rooms["bw_field_center"], rooms["bw_field_e"], "east")
    # Bottom row (east-west)
    connect(rooms["bw_field_sw"], rooms["bw_field_s"], "east")
    connect(rooms["bw_field_s"], rooms["bw_field_se"], "east")
    exit_count += 12

    # Columns (north-south)
    connect(rooms["bw_field_nw"], rooms["bw_field_w"], "south")
    connect(rooms["bw_field_w"], rooms["bw_field_sw"], "south")
    connect(rooms["bw_field_n"], rooms["bw_field_center"], "south")
    connect(rooms["bw_field_center"], rooms["bw_field_s"], "south")
    connect(rooms["bw_field_ne"], rooms["bw_field_e"], "south")
    connect(rooms["bw_field_e"], rooms["bw_field_se"], "south")
    exit_count += 12

    # ── Brightwater Underground ────────────────────────────────────
    # Hidden trapdoor in the barn floor — the Brightwaters' secret entrance
    barn_trap_ab, barn_trap_ba = connect_door(
        rooms["bw_barn"], rooms["bw_cellar"], "down",
        key="a trapdoor",
        closed_ab=(
            "The barn floor is covered with a thick layer of cotton "
            "fibers and loose straw. Nothing unusual is visible."
        ),
        open_ab=(
            "A trapdoor in the barn floor stands open beneath a "
            "scattering of cotton fibers, revealing a root cellar below."
        ),
        closed_ba=(
            "A sturdy trapdoor is set into the ceiling above, its "
            "underside reinforced with iron bands."
        ),
        open_ba=(
            "The trapdoor above hangs open, cotton fibers drifting "
            "down from the barn floor."
        ),
        door_name="trapdoor",
    )
    barn_trap_ab.is_hidden = True
    barn_trap_ab.find_dc = 16

    connect(rooms["bw_cellar"], rooms["bw_tunnel"], "south")
    connect(rooms["bw_tunnel"], rooms["bw_chamber"], "south")
    connect(rooms["bw_chamber"], rooms["bw_exit"], "east")
    exit_count += 8

    # Hidden exit surfaces near the south fork — concealed by brambles
    tunnel_exit_ab, tunnel_exit_ba = connect_door(
        rooms["bw_exit"], rooms["south_fork_end"], "up",
        key="a gap in the brambles",
        closed_ab=(
            "Roots and packed earth form the ceiling. There is no "
            "obvious way out."
        ),
        open_ab=(
            "A narrow gap in the brambles above lets daylight in, "
            "just wide enough to squeeze through."
        ),
        closed_ba=(
            "Dense brambles and undergrowth cover the ground here. "
            "Nothing unusual is visible."
        ),
        open_ba=(
            "A gap in the brambles reveals a dark hole descending "
            "into the earth beneath the hedgerow."
        ),
        door_name="gap",
    )
    tunnel_exit_ba.is_hidden = True
    tunnel_exit_ba.find_dc = 18
    exit_count += 2

    # ── Brightwater prepper stash (locked chest in the tunnel) ────
    stash = create_object(
        WorldChest,
        key="a sturdy halfling chest",
        location=rooms["bw_tunnel"],
        nohome=True,
    )
    stash.is_locked = True
    stash.lock_dc = 16
    stash.key_tag = "brightwater_stash"
    stash.relock_seconds = 3600  # relocks after 1 hour
    stash.db.desc = (
        "A squat, iron-banded chest built to halfling proportions, "
        "pushed against the tunnel wall and half-concealed behind "
        "a stack of empty grain sacks. The lock is sturdy and well-"
        "oiled — someone maintains this regularly. Whatever the "
        "Brightwaters are keeping in here, they want it ready to "
        "grab in a hurry."
    )

    # ── Stash key hidden in the drying shed ──────────────────────
    stash_key = create_object(
        KeyItem,
        key="a small iron key",
        location=rooms["bw_shed"],
        nohome=True,
    )
    stash_key.key_tag = "brightwater_stash"
    stash_key.is_hidden = True
    stash_key.find_dc = 14
    stash_key.db.desc = (
        "A small iron key on a leather thong, tucked behind a loose "
        "board in the drying rack. It looks like it fits a padlock "
        "or chest lock."
    )

    # ── Abandoned Farm ─────────────────────────────────────────────
    connect(rooms["ab_path"], rooms["ab_yard"], "east")
    connect(rooms["ab_yard"], rooms["ab_barn"], "north")
    exit_count += 4

    # Abandoned fields: 4×2 grid south of yard
    connect(rooms["ab_yard"], rooms["ab_field_1"], "south")
    exit_count += 2

    # Top row (east-west)
    connect(rooms["ab_field_1"], rooms["ab_field_2"], "east")
    connect(rooms["ab_field_2"], rooms["ab_field_3"], "east")
    connect(rooms["ab_field_3"], rooms["ab_field_4"], "east")
    exit_count += 6

    # Bottom row (east-west)
    connect(rooms["ab_field_5"], rooms["ab_field_6"], "east")
    connect(rooms["ab_field_6"], rooms["ab_field_7"], "east")
    connect(rooms["ab_field_7"], rooms["ab_field_8"], "east")
    exit_count += 6

    # Columns (north-south)
    connect(rooms["ab_field_1"], rooms["ab_field_5"], "south")
    connect(rooms["ab_field_2"], rooms["ab_field_6"], "south")
    connect(rooms["ab_field_3"], rooms["ab_field_7"], "south")
    connect(rooms["ab_field_4"], rooms["ab_field_8"], "south")
    exit_count += 8

    print(f"  Created {exit_count} exits.")

    # ══════════════════════════════════════════════════════════════════
    # 3. TAG ROOMS — zone, district, terrain
    # ══════════════════════════════════════════════════════════════════

    all_rooms = list(rooms.values())
    for room in all_rooms:
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # Terrain types — outdoor rural for most farm rooms
    outdoor_rural = [
        rooms["farm_road_1"], rooms["farm_road_2"],
        rooms["farm_road_meadow"], rooms["farm_road_oak"],
        rooms["farm_road_hill"], rooms["farm_road_crossroads"],
        rooms["farm_road_west"], rooms["farm_road_cotton"],
        rooms["farm_road_mill"],
        rooms["south_fork_1"], rooms["south_fork_2"],
        rooms["south_fork_3"], rooms["south_fork_end"],
        rooms["bw_track"], rooms["bw_yard"], rooms["bw_well"],
        rooms["bw_field_nw"], rooms["bw_field_n"], rooms["bw_field_ne"],
        rooms["bw_field_w"], rooms["bw_field_center"], rooms["bw_field_e"],
        rooms["bw_field_sw"], rooms["bw_field_s"], rooms["bw_field_se"],
        rooms["gw_lane"], rooms["gw_garden"],
        *[gw_grid[r][c] for r in range(3) for c in range(7)],
        rooms["ab_path"], rooms["ab_yard"],
        rooms["ab_field_1"], rooms["ab_field_2"],
        rooms["ab_field_3"], rooms["ab_field_4"],
        rooms["ab_field_5"], rooms["ab_field_6"],
        rooms["ab_field_7"], rooms["ab_field_8"],
    ]
    outdoor_rural.append(rooms["bw_shed"])
    outdoor_rural.append(rooms["weavers_track"])
    for room in outdoor_rural:
        room.set_terrain(TerrainType.RURAL.value)

    # Indoor / structure rooms — urban terrain
    indoor_rooms = [
        rooms["windmill"],
        rooms["weaving_house"],
        rooms["bw_barn"],
        rooms["bw_farmhouse"],
        rooms["ab_barn"],
        rooms["gw_homestead"], rooms["gw_barn"],
    ]
    for room in indoor_rooms:
        room.set_terrain(TerrainType.URBAN.value)

    # Shop rooms — no combat
    # (RoomProcessing rooms like windmill/weaving_house already have allow_combat=False)
    rooms["bw_farmhouse"].allow_combat = False
    rooms["gw_homestead"].allow_combat = False

    # Underground rooms
    underground_rooms = [
        rooms["bw_cellar"], rooms["bw_tunnel"],
        rooms["bw_chamber"], rooms["bw_exit"],
    ]
    for room in underground_rooms:
        room.set_terrain(TerrainType.UNDERGROUND.value)

    print("  Tagged all rooms with zone, district, and terrain.")

    # ── Mob area tags (for mob wandering boundaries) ────────────────
    abandoned_farm_rooms = [
        rooms["ab_path"], rooms["ab_yard"], rooms["ab_barn"],
        rooms["ab_field_1"], rooms["ab_field_2"],
        rooms["ab_field_3"], rooms["ab_field_4"],
        rooms["ab_field_5"], rooms["ab_field_6"],
        rooms["ab_field_7"], rooms["ab_field_8"],
    ]
    for room in abandoned_farm_rooms:
        room.tags.add("abandoned_farm", category="mob_area")

    wheat_farm_rooms = [
        rooms["gw_lane"], rooms["gw_garden"],
        *[gw_grid[r][c] for r in range(3) for c in range(7)],
    ]
    for room in wheat_farm_rooms:
        room.tags.add("wheat_farm", category="mob_area")

    cotton_farm_rooms = [
        rooms["bw_yard"],
        rooms["bw_field_nw"], rooms["bw_field_n"], rooms["bw_field_ne"],
        rooms["bw_field_w"], rooms["bw_field_center"], rooms["bw_field_e"],
        rooms["bw_field_sw"], rooms["bw_field_s"], rooms["bw_field_se"],
    ]
    for room in cotton_farm_rooms:
        room.tags.add("cotton_farm", category="mob_area")

    print("  Tagged farm rooms with mob_area.")

    # ══════════════════════════════════════════════════════════════════
    # 4. FUTURE CONNECTION NOTES
    # ══════════════════════════════════════════════════════════════════
    # windmill (western terminus) → future: road continues west?
    # south_fork_end → connects up from bw_exit (halfling tunnel)
    # abandoned farm fields → potential dungeon entrance underground

    # ── Region map cell tags ────────────────────────────────────────
    _rt = "millholm_region"

    # Windmill (western terminus)
    rooms["windmill"].tags.add(f"{_rt}:windmill", category="map_cell")

    # Farm road (E-W): split into 4 chunks matching region cells
    for key in ["farm_road_1", "farm_road_2"]:
        rooms[key].tags.add(f"{_rt}:farm_road_w", category="map_cell")
    for key in ["farm_road_meadow", "farm_road_oak", "farm_road_hill"]:
        rooms[key].tags.add(f"{_rt}:farm_road_mid", category="map_cell")
    for key in ["farm_road_crossroads", "farm_road_west"]:
        rooms[key].tags.add(f"{_rt}:farm_road_e", category="map_cell")
    for key in ["farm_road_cotton", "farm_road_mill"]:
        rooms[key].tags.add(f"{_rt}:farm_road_far_e", category="map_cell")

    # Wheat farm → region "wheat_farm" cell
    for key in ["gw_lane", "gw_garden", "gw_homestead", "gw_barn"]:
        rooms[key].tags.add(f"{_rt}:wheat_farm", category="map_cell")
    for row in gw_grid:
        for room in row:
            room.tags.add(f"{_rt}:wheat_farm", category="map_cell")

    # Cotton farm → region "cotton_farm" cell
    for key in ["bw_track", "bw_yard", "bw_barn", "bw_shed", "bw_well",
                "bw_farmhouse", "bw_field_nw", "bw_field_n", "bw_field_ne",
                "bw_field_w", "bw_field_center", "bw_field_e",
                "bw_field_sw", "bw_field_s", "bw_field_se"]:
        rooms[key].tags.add(f"{_rt}:cotton_farm", category="map_cell")

    # South fork road → region "south_fork" cell
    for key in ["south_fork_1", "south_fork_2", "south_fork_3", "south_fork_end"]:
        rooms[key].tags.add(f"{_rt}:south_fork", category="map_cell")
    # Weaving house spur
    for key in ["weavers_track", "weaving_house"]:
        rooms[key].tags.add(f"{_rt}:south_fork", category="map_cell")

    print(f"  Tagged farms rooms with {_rt} map_cell tags.")

    print("  Millholm Farms complete.\n")
    return rooms

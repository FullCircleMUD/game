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
from enums.room_crafting_type import RoomCraftingType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_crafting import RoomCrafting
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect, connect_door


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

    rooms["sailing_club"] = create_object(
        RoomGateway,
        key="Millholm Junior Sailing Club",
        attributes=[
            ("max_height", 0),
            ("desc",
             "A rickety wooden boathouse perched on the lake's eastern "
             "shore, its planks weathered silver and its roof patched "
             "with tar and canvas. A hand-painted sign over the door "
             "reads 'MILLHOLM JUNIOR SAILING CLUB' in wobbly letters, "
             "with a crude painting of a sailboat underneath. Inside, "
             "a jumble of small dinghies, coils of rope, and canvas "
             "sails compete for space with oars, rudders, and a "
             "suspicious number of buckets. The smell of varnish, "
             "damp wood, and lake water fills the air. A noticeboard "
             "is pinned with tide charts, race results, and a stern "
             "warning about not feeding the ducks."),
            ("details", {
                "sign": (
                    "A hand-painted wooden sign, clearly the work of "
                    "an enthusiastic child. The letters are uneven and "
                    "the sailboat looks more like a duck with a stick "
                    "in it. Someone has added 'EST. AGES AGO' in smaller "
                    "letters beneath."
                ),
                "dinghies": (
                    "Half a dozen small sailing dinghies in various "
                    "states of repair. Some have names painted on the "
                    "bows — 'The Unsinkable', 'Mum Says No', 'Floaty "
                    "McFloat'. One has a large hole in the hull and a "
                    "note reading 'DO NOT USE — Timmy'."
                ),
                "noticeboard": (
                    "A cork noticeboard bristling with pins and scraps "
                    "of paper. Race results ('1st: The Unsinkable, 2nd: "
                    "everyone else, 3rd: Timmy (capsized)'), tide charts "
                    "that may or may not be accurate, and a notice in "
                    "large letters: 'ABSOLUTELY NO FEEDING THE DUCKS. "
                    "THEY KNOW WHAT THEY DID.'"
                ),
                "buckets": (
                    "An alarming number of buckets. Apparently bailing "
                    "is a core part of the sailing experience here."
                ),
            }),
        ],
    )

    rooms["far_shore"] = create_object(
        RoomGateway,
        key="Far Shore Landing",
        attributes=[
            ("max_height", 1),
            ("desc",
             "A rough wooden landing stage on the far side of the lake, "
             "little more than a few planks nailed to posts driven into "
             "the mud. The shore here is wild and untended — dense scrub "
             "presses close to the water's edge, and the trees beyond "
             "are thick and dark. A faded signpost points back across "
             "the lake toward Millholm, barely visible as a smudge of "
             "chimney smoke on the southern horizon."),
            ("details", {
                "landing": (
                    "A basic landing stage — four posts and some planks. "
                    "It wobbles when you step on it. Rope loops are "
                    "tied to the posts for mooring."
                ),
                "signpost": (
                    "A weathered wooden signpost. One arm reads "
                    "'MILLHOLM' with an arrow pointing south across the "
                    "water. The other arm is blank — whatever was written "
                    "there has been worn away."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # SHALLOWS ROW — max_depth=-1, wading/swimming depth
    # ══════════════════════════════════════════════════════════════════

    rooms["shallows_w"] = create_object(
        RoomBase,
        key="Sheltered Shallows",
        attributes=[
            ("max_height", 1),
            ("max_depth", -1),
            ("desc",
             "Knee-deep water laps gently in a sheltered cove beneath "
             "overhanging willows. The bottom is soft mud and sand, "
             "and water weed sways lazily in the current. Minnows dart "
             "between your feet and dragonflies skim the surface. The "
             "water is surprisingly warm here, sheltered from the wind "
             "by the curve of the shore."),
            ("details", {
                "water weed": (
                    "Long strands of green water weed, rooted in the "
                    "silty bottom and trailing with the current. Tiny "
                    "snails cling to the fronds."
                ),
                "minnows": (
                    "Silver minnows, no bigger than a finger, darting "
                    "in and out of the weed in nervous shoals."
                ),
            }),
        ],
    )

    rooms["shallows_c"] = create_object(
        RoomBase,
        key="Lake Shallows",
        attributes=[
            ("max_height", 1),
            ("max_depth", -1),
            ("desc",
             "The lake is waist-deep here, the water clear enough to "
             "see the pebbly bottom. Reeds grow in clumps, their green "
             "stems swaying with each ripple. Further out the water "
             "deepens to a dark blue-green. Ducks paddle past with "
             "studied indifference, and a coot dives suddenly, leaving "
             "only a ring of ripples behind."),
            ("details", {
                "reeds": (
                    "Tall green reeds growing in dense clumps from the "
                    "lake bed. Their stems are hollow and creak when "
                    "they rub together in the wind."
                ),
                "bottom": (
                    "A pebbly lake bed of smooth, rounded stones in "
                    "shades of grey, brown, and amber. The water is "
                    "clear enough to count them."
                ),
            }),
        ],
    )

    rooms["shallows_e"] = create_object(
        RoomBase,
        key="Rocky Shallows",
        attributes=[
            ("max_height", 1),
            ("max_depth", -1),
            ("desc",
             "Flat slabs of grey stone extend out into the lake here, "
             "forming a natural shelf just below the surface. The water "
             "is only ankle-deep over the rocks but drops away sharply "
             "at the edge. Fish gather in the deeper water just beyond, "
             "and a kingfisher perches on a dead branch overhead, "
             "watching them with fierce concentration."),
            ("details", {
                "rocks": (
                    "Flat grey stone, smooth and algae-slicked. Natural "
                    "ledges and crevices harbour small crabs and "
                    "freshwater shrimp."
                ),
                "kingfisher": (
                    "A brilliant blue-and-orange kingfisher, utterly "
                    "still on its perch. It watches the water below "
                    "with murderous intent."
                ),
            }),
        ],
    )

    rooms["shallows_dock"] = create_object(
        RoomBase,
        key="Clubhouse Shallows",
        attributes=[
            ("max_height", 1),
            ("max_depth", -1),
            ("desc",
             "The water alongside the sailing club is churned and "
             "muddy from the constant launching and beaching of small "
             "boats. Rope ends trail in the water, and a lost oar "
             "bobs gently against the dock posts. The bottom here is "
             "thick mud — your feet sink in with every step. A faded "
             "buoy marks the edge of the swimming area."),
            ("details", {
                "buoy": (
                    "A red-and-white painted buoy, its paint peeling, "
                    "bobbing on a short chain. A sign on it reads "
                    "'NO SWIMMING BEYOND THIS POINT' but the letters "
                    "are almost illegible."
                ),
                "oar": (
                    "A wooden oar, waterlogged and drifting. Someone's "
                    "name is carved into the handle but the water has "
                    "made it unreadable."
                ),
            }),
        ],
    )

    rooms["shallows_yard"] = create_object(
        RoomBase,
        key="Boatyard Shallows",
        attributes=[
            ("max_height", 1),
            ("max_depth", -1),
            ("desc",
             "The water at the foot of the boatyard slipway is shallow "
             "and littered with wood shavings, off-cuts, and the "
             "occasional dropped nail. The slipway's greased timbers "
             "extend down into the water, and the bottom is compacted "
             "gravel — laid deliberately to give newly launched boats "
             "a clean surface to slide into the lake."),
            ("details", {
                "slipway": (
                    "Heavy timber beams slicked with tallow, angled "
                    "down into the water. This is where finished boats "
                    "are launched — pushed down the greased timbers "
                    "into the lake."
                ),
                "shavings": (
                    "Wood shavings and off-cuts floating on the surface, "
                    "evidence of the boatyard above. A few have "
                    "collected against the dock posts in a soggy raft."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # DEEP ROW — max_depth=-2, proper swimming/diving depth
    # ══════════════════════════════════════════════════════════════════

    rooms["deep_w"] = create_object(
        RoomBase,
        key="Deep Water - Western Reach",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "The lake is deep here, the water a dark, cold green. The "
             "bottom is invisible — just a murky darkness below your "
             "feet. Lily pads cluster on the surface, their white "
             "flowers open to the sky. The western shore is a distant "
             "line of willows. Something large moves below the surface, "
             "sending a slow ripple outward."),
            ("details", {
                "lily pads": (
                    "Broad green lily pads, each the size of a dinner "
                    "plate, floating on the dark water. White flowers "
                    "with yellow centres bloom among them."
                ),
                "ripple": (
                    "A slow, spreading ripple from something moving "
                    "below the surface. A large fish, perhaps. Or "
                    "perhaps not."
                ),
            }),
        ],
    )

    rooms["deep_c"] = create_object(
        RoomBase,
        key="Deep Water - Lake Centre",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "The deepest part of the lake. The water is inky dark "
             "and bitterly cold. The shore seems far away in every "
             "direction — just a thin line of green on the horizon. "
             "The surface is glassy and still, broken only by the "
             "occasional ring of a rising fish. There is a profound "
             "silence out here, away from the shore. Just water, sky, "
             "and the faint slap of wavelets."),
            ("details", {
                "water": (
                    "Deep, cold, and dark. You cannot see the bottom. "
                    "The water has the particular stillness of a lake "
                    "that has been here for a very long time."
                ),
                "sky": (
                    "The sky is reflected perfectly in the still water, "
                    "creating a dizzying sense of floating between two "
                    "skies. Clouds drift below your feet."
                ),
            }),
        ],
    )

    rooms["deep_e"] = create_object(
        RoomBase,
        key="Deep Water - Eastern Reach",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "Deep water over a rocky bottom — you can just make out "
             "the dark shapes of boulders far below through the clear "
             "water. The eastern shore and its jumble of rocks is "
             "visible to the south. A cormorant surfaces nearby, a "
             "fish clamped in its beak, and takes off with heavy "
             "wingbeats, trailing droplets of water."),
            ("details", {
                "boulders": (
                    "Dark shapes on the lake bed, far below. Boulders "
                    "or perhaps the remains of something built — it's "
                    "hard to tell from the surface."
                ),
                "cormorant": (
                    "A sleek black cormorant, diving and surfacing "
                    "with fish. It watches you with a suspicious "
                    "orange eye before flying off."
                ),
            }),
        ],
    )

    rooms["deep_dock"] = create_object(
        RoomBase,
        key="Deep Water - Off the Dock",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "Open water beyond the sailing club's mooring buoys. The "
             "bottom drops away steeply here — the dock was built on "
             "the edge of a natural shelf. Boat hulls pass overhead "
             "when the club is busy, their shadows gliding across the "
             "depths. A sunken rowing boat lies on the bottom, half "
             "buried in silt, its name still faintly visible on the "
             "stern."),
            ("details", {
                "sunken boat": (
                    "A small rowing boat resting on the lake bed, "
                    "its timbers dark with waterlogging. The name "
                    "'Timmy's Revenge' is just visible on the stern. "
                    "Fish shelter in the shadow of the hull."
                ),
                "buoys": (
                    "Red-and-white mooring buoys bobbing on the "
                    "surface, marking the edge of the swimming area "
                    "and the start of the sailing channel."
                ),
            }),
        ],
    )

    rooms["deep_yard"] = create_object(
        RoomBase,
        key="Deep Water - Off the Slipway",
        attributes=[
            ("max_height", 1),
            ("max_depth", -2),
            ("desc",
             "Deep water at the foot of the boatyard slipway. The "
             "greased timbers of the launch ramp extend down into "
             "the darkness. Wood shavings and sawdust drift on the "
             "surface. The bottom here is littered with the debris "
             "of years of boatbuilding — dropped tools, bent nails, "
             "offcuts of timber. An enterprising crayfish has made "
             "its home in a discarded bucket."),
            ("details", {
                "slipway": (
                    "The boatyard's launch ramp, its greased timbers "
                    "extending down into the deep water. The wood is "
                    "slimy with algae below the waterline."
                ),
                "crayfish": (
                    "A large freshwater crayfish, dark brown and "
                    "armoured, peering out from a rusty bucket on "
                    "the lake bed. It waves its claws at you "
                    "threateningly."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════════
    # UNDERWATER CAVE — hidden grotto off deep_c, bloodmoss harvesting
    # ══════════════════════════════════════════════════════════════════

    rooms["underwater_cave"] = create_object(
        RoomHarvesting,
        key="Underwater Grotto",
        attributes=[
            ("desc",
             "A natural cavity in the rock beneath the lake bed, just "
             "large enough to swim into. The walls are slick with algae "
             "and the water glows a faint, eerie green — bioluminescent "
             "organisms cling to every surface. Thick clumps of dark "
             "red moss grow from the cracks in the stone, swaying gently "
             "in the slow current. Air bubbles trickle upward from a "
             "fissure in the floor, catching the green light as they "
             "rise. The entrance behind you is a dark oval in the rock, "
             "barely visible from outside."),
            ("max_height", 0),
            ("max_depth", -1),
            ("resource_id", 14),       # Bloodmoss
            ("resource_count", 0),     # spawn script sets amount
            ("abundance_threshold", 3),
            ("harvest_height", -1),    # must be underwater to harvest
            ("harvest_command", "gather"),
            ("desc_abundant",
             "Thick clumps of dark red bloodmoss grow from every crack "
             "and crevice, swaying in the slow current. There is plenty "
             "to gather here."),
            ("desc_scarce",
             "A few sparse clumps of bloodmoss cling to the walls, "
             "their fronds thin and pale. The supply is running low."),
            ("desc_depleted",
             "The rock walls are bare — the bloodmoss has been picked "
             "clean. Only bare stone and algae remain."),
            ("details", {
                "moss": (
                    "Dark red moss with thick, fleshy fronds. It clings "
                    "to the rock with surprising tenacity. When torn "
                    "free it bleeds a dark ichor — hence the name. "
                    "Alchemists prize it for healing potions."
                ),
                "light": (
                    "A faint green bioluminescence coats the cave walls. "
                    "Tiny organisms, each no bigger than a pinhead, "
                    "glow softly in the darkness. The effect is "
                    "beautiful and deeply unsettling."
                ),
                "bubbles": (
                    "A steady trickle of air bubbles rises from a "
                    "crack in the cave floor. Not enough to breathe — "
                    "but proof that something lies deeper still."
                ),
            }),
            ("always_lit", True),  # bioluminescence
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # BOATYARD — east of sailing club
    # ══════════════════════════════════════════════════════════════════

    rooms["boatyard"] = create_object(
        RoomCrafting,
        key="Lakeside Boatyard",
        attributes=[
            ("crafting_type", RoomCraftingType.SHIPYARD.value),
            ("mastery_level", 1),
            ("craft_cost", 5),
            ("max_height", 0),
            ("desc",
             "A small open-air boatyard beside the sailing club, "
             "little more than a slipway, a sawhorse, and a lean-to "
             "shelter stacked with timber. A half-built hull sits on "
             "the slipway, its ribs curving upward like a whale's "
             "skeleton. Tools hang from nails on the shelter posts — "
             "saws, planes, hammers, pots of tar, and coils of hemp "
             "rope. The smell of fresh-cut wood and pine tar hangs "
             "heavy in the air. A battered sign reads 'BOATS BUILT "
             "HERE — RESULTS MAY VARY'."),
            ("details", {
                "hull": (
                    "The skeleton of a small boat — a cog, by the look "
                    "of the broad, flat bottom. The ribs are pegged "
                    "together with oak dowels and the keel is a single "
                    "piece of elm. It's about half finished."
                ),
                "tools": (
                    "A basic but serviceable set of boatbuilding tools. "
                    "Handsaws, drawknives, caulking irons, a mallet, "
                    "and several pots of Stockholm tar. Nothing fancy, "
                    "but enough to build a small vessel."
                ),
                "sign": (
                    "'BOATS BUILT HERE — RESULTS MAY VARY'. Someone "
                    "has scratched 'Timmy woz here' underneath, and "
                    "below that, in different handwriting, 'Timmy's "
                    "boat sank'."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # SUNKEN WRECK — lootable fixture in deep_dock
    # ══════════════════════════════════════════════════════════════════

    from typeclasses.world_objects.chest import WorldChest

    wreck = create_object(
        WorldChest,
        key="a sunken rowing boat",
        location=rooms["deep_dock"],
        nohome=True,
    )
    wreck.db.desc = (
        "The remains of a small rowing boat resting on the lake bed, "
        "its timbers dark and swollen with waterlogging. The name "
        "'Timmy's Revenge' is just visible on the stern in faded "
        "paint. Fish shelter in the shadow of the hull, and silt has "
        "drifted against one side. Something glints in the mud "
        "beneath the overturned bow."
    )
    wreck.is_open = True  # no need to open — just take from it
    wreck.loot_gold_max = 5
    wreck.room_vertical_position = -2
    wreck.visible_max_height = -1  # only visible at depth -1 or below
    wreck.tags.add(ZONE, category="zone")
    wreck.tags.add(DISTRICT, category="district")

    print(f"  Created {len(rooms)} northern rooms.")

    # ══════════════════════════════════════════════════════════════════
    # EXITS — lake shore connections
    # ══════════════════════════════════════════════════════════════════

    connect(rooms["lake_shore_west"], rooms["lake_shore"], "east")
    connect(rooms["lake_shore"], rooms["lake_shore_east"], "east")

    # Eastern shore → Sailing Club (door)
    connect_door(
        rooms["lake_shore_east"], rooms["sailing_club"], "east",
        key="a weathered door",
        closed_ab=(
            "A weathered wooden door with a hand-painted sailboat on it "
            "leads east into a boathouse."
        ),
        open_ab=(
            "Through the open door you can see a cluttered boathouse "
            "full of dinghies and rope."
        ),
        closed_ba=(
            "A weathered door leads west to the lake shore."
        ),
        open_ba=(
            "The rocky lake shore is visible through the open door."
        ),
        door_name="door",
    )

    # Sailing club → Boatyard
    connect(rooms["sailing_club"], rooms["boatyard"], "east")

    # Shallows row (east-west)
    connect(rooms["shallows_w"], rooms["shallows_c"], "east")
    connect(rooms["shallows_c"], rooms["shallows_e"], "east")
    connect(rooms["shallows_e"], rooms["shallows_dock"], "east")
    connect(rooms["shallows_dock"], rooms["shallows_yard"], "east")

    # Shore → Shallows (north-south)
    connect(rooms["lake_shore_west"], rooms["shallows_w"], "north")
    connect(rooms["lake_shore"], rooms["shallows_c"], "north")
    connect(rooms["lake_shore_east"], rooms["shallows_e"], "north")
    connect(rooms["sailing_club"], rooms["shallows_dock"], "north")
    connect(rooms["boatyard"], rooms["shallows_yard"], "north")

    # Gateway destinations — sail across the lake (BASIC cartography + Cog)
    rooms["sailing_club"].destinations = [
        {
            "key": "far_shore",
            "label": "Far Shore Landing",
            "destination": rooms["far_shore"],
            "travel_description": (
                "You push off from the rickety dock and catch the wind. "
                "The little boat skims across the glassy water, ducks "
                "scattering in your wake. The far shore grows slowly "
                "closer until you bump against the landing stage."
            ),
            "conditions": {"boat_level": 1, "food_cost": 1},
        },
    ]
    rooms["far_shore"].destinations = [
        {
            "key": "sailing_club",
            "label": "Millholm Junior Sailing Club",
            "destination": rooms["sailing_club"],
            "travel_description": (
                "You cast off from the landing and sail south across "
                "the lake. The smudge of Millholm's chimney smoke grows "
                "clearer, and before long the rickety boathouse comes "
                "into view."
            ),
            "conditions": {"boat_level": 1, "food_cost": 1},
        },
    ]

    # Deep row (east-west)
    connect(rooms["deep_w"], rooms["deep_c"], "east")
    connect(rooms["deep_c"], rooms["deep_e"], "east")
    connect(rooms["deep_e"], rooms["deep_dock"], "east")
    connect(rooms["deep_dock"], rooms["deep_yard"], "east")

    # Shallows → Deep (north-south)
    connect(rooms["shallows_w"], rooms["deep_w"], "north")
    connect(rooms["shallows_c"], rooms["deep_c"], "north")
    connect(rooms["shallows_e"], rooms["deep_e"], "north")
    connect(rooms["shallows_dock"], rooms["deep_dock"], "north")
    connect(rooms["shallows_yard"], rooms["deep_yard"], "north")

    # Trick exits — deep row edges loop back
    trick_deep_w = create_object(
        ExitVerticalAware,
        key="Deep Water - Western Reach",
        location=rooms["deep_w"],
        destination=rooms["deep_w"],
    )
    trick_deep_w.set_direction("west")

    trick_deep_e = create_object(
        ExitVerticalAware,
        key="Deep Water - Off the Slipway",
        location=rooms["deep_yard"],
        destination=rooms["deep_yard"],
    )
    trick_deep_e.set_direction("east")

    # Deep row north loops back (no further north) — except deep_c
    for rkey in ["deep_w", "deep_e", "deep_dock", "deep_yard"]:
        trick_n = create_object(
            ExitVerticalAware,
            key=rooms[rkey].key,
            location=rooms[rkey],
            destination=rooms[rkey],
        )
        trick_n.set_direction("north")

    # deep_c north: trick loop at heights 0 to -1, cave at depth -2
    trick_c_n = create_object(
        ExitVerticalAware,
        key=rooms["deep_c"].key,
        location=rooms["deep_c"],
        destination=rooms["deep_c"],
    )
    trick_c_n.set_direction("north")
    trick_c_n.required_min_height = -1
    trick_c_n.required_max_height = 1

    # Hidden cave entrance — only visible at depth -2
    exit_to_cave = create_object(
        ExitVerticalAware,
        key="a dark opening in the rocks",
        location=rooms["deep_c"],
        destination=rooms["underwater_cave"],
    )
    exit_to_cave.set_direction("north")
    exit_to_cave.required_min_height = -2
    exit_to_cave.required_max_height = -2
    exit_to_cave.arrival_heights = {-2: 0}

    # Return exit from cave back to deep_c (at depth -2)
    exit_from_cave = create_object(
        ExitVerticalAware,
        key="the submerged passage",
        location=rooms["underwater_cave"],
        destination=rooms["deep_c"],
    )
    exit_from_cave.set_direction("south")
    exit_from_cave.arrival_heights = {0: -2}

    # Trick exits — shallows edges loop back to themselves
    trick_shallows_w = create_object(
        ExitVerticalAware,
        key="Sheltered Shallows",
        location=rooms["shallows_w"],
        destination=rooms["shallows_w"],
    )
    trick_shallows_w.set_direction("west")

    trick_shallows_e = create_object(
        ExitVerticalAware,
        key="Boatyard Shallows",
        location=rooms["shallows_yard"],
        destination=rooms["shallows_yard"],
    )
    trick_shallows_e.set_direction("east")

    # Trick exit — west from western shore loops back to itself
    from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
    trick_west = create_object(
        ExitVerticalAware,
        key="Western Lake Shore",
        location=rooms["lake_shore_west"],
        destination=rooms["lake_shore_west"],
    )
    trick_west.set_direction("west")

    print("  Created 5 lake shore exits.")

    # ══════════════════════════════════════════════════════════════════
    # TAGS — zone, district, terrain, properties
    # ══════════════════════════════════════════════════════════════════

    # Lake track is town-side of the passage — tagged as town
    rooms["lake_track"].tags.add(ZONE, category="zone")
    rooms["lake_track"].tags.add("millholm_town", category="district")
    rooms["lake_track"].tags.add("millholm_town:lake_track", category="map_cell")
    rooms["lake_track"].tags.add("millholm_region:lake", category="map_cell")
    rooms["lake_track"].set_terrain(TerrainType.PLAINS.value)
    rooms["lake_track"].sheltered = False

    # Lake shore rooms are the lake district
    lake_rooms = [
        rooms["lake_shore"], rooms["lake_shore_west"],
        rooms["lake_shore_east"], rooms["sailing_club"],
        rooms["far_shore"], rooms["boatyard"],
        rooms["shallows_w"], rooms["shallows_c"], rooms["shallows_e"],
        rooms["shallows_dock"], rooms["shallows_yard"],
        rooms["deep_w"], rooms["deep_c"], rooms["deep_e"],
        rooms["deep_dock"], rooms["deep_yard"],
    ]
    for room in lake_rooms:
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.sheltered = False

    # Shore/buildings = COASTAL, shallows = WATER
    for room in [rooms["lake_shore"], rooms["lake_shore_west"],
                 rooms["lake_shore_east"], rooms["sailing_club"],
                 rooms["far_shore"], rooms["boatyard"]]:
        room.set_terrain(TerrainType.COASTAL.value)
    for room in [rooms["shallows_w"], rooms["shallows_c"],
                 rooms["shallows_e"], rooms["shallows_dock"],
                 rooms["shallows_yard"],
                 rooms["deep_w"], rooms["deep_c"], rooms["deep_e"],
                 rooms["deep_dock"], rooms["deep_yard"]]:
        room.set_terrain(TerrainType.WATER.value)

    rooms["underwater_cave"].set_terrain(TerrainType.UNDERGROUND.value)
    rooms["underwater_cave"].tags.add(ZONE, category="zone")
    rooms["underwater_cave"].tags.add(DISTRICT, category="district")

    # Mob area tags for zone spawn script
    for room in [rooms["lake_shore"], rooms["lake_shore_west"],
                 rooms["lake_shore_east"]]:
        room.tags.add("lake_shore", category="mob_area")
    for room in [rooms["shallows_w"], rooms["shallows_c"],
                 rooms["shallows_e"], rooms["shallows_dock"],
                 rooms["shallows_yard"]]:
        room.tags.add("lake_shore", category="mob_area")
        room.tags.add("lake_shallows", category="mob_area")
    for room in [rooms["deep_w"], rooms["deep_c"], rooms["deep_e"],
                 rooms["deep_dock"], rooms["deep_yard"]]:
        room.tags.add("lake_deep", category="mob_area")

    print("  Tagged all northern rooms (zone, district, terrain, weather).")
    print("  Millholm Lake complete.\n")

    return rooms

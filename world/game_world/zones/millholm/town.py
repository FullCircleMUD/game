"""
Millholm Town — the central hub of the Millholm zone.

Builds rooms and exits for the town district including:
- The Old Trade Way (east-west road, 9 segments + 3x3 market square)
- 3x3 Market Square with EW/NS crossroads
- South Road (4 segments from sq_s to south gate)
- The Harvest Moon Inn (with stairwell, cellar, upstairs hallway, bedrooms)
- Crafting/processing shops (bakery, smithy, leathershop, tailor, woodshop, apothecary)
- Guild halls (warriors, mages, temple) with back rooms
- Bank, general store, stables, post office, distillery
- The Broken Crown tavern, Gaol, Beggar's Alley
- Residential houses
- Cemetery (north road, dead end)
- South Gate (town boundary, connects to Southern District)
- District intersection points (farms, woods, sewers, southern district)

Usage:
    from world.game_world.millholm_town import build_millholm_town
    build_millholm_town()
"""

from evennia import create_object, ObjectDB

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_bank import RoomBank
from typeclasses.terrain.rooms.room_crafting import RoomCrafting
from typeclasses.terrain.rooms.room_inn import RoomInn
from typeclasses.terrain.rooms.room_postoffice import RoomPostOffice
from typeclasses.terrain.rooms.room_processing import RoomProcessing
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from utils.exit_helpers import connect_bidirectional_exit, connect_bidirectional_door_exit


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_town"


def build_millholm_town(one_way_limbo=False):
    """Build the Millholm Town district and connect Limbo to the inn.

    Args:
        one_way_limbo: If True, create only a one-way exit from Limbo to the
            inn (players can't walk back to Limbo). Default False (two-way).
    """
    limbo = ObjectDB.objects.get(id=2)
    rooms = {}

    # ══════════════════════════════════════════════════════════════════
    # 1. CREATE ROOMS
    # ══════════════════════════════════════════════════════════════════

    # ── The Harvest Moon (Inn) ────────────────────────────────────────
    rooms["inn"] = create_object(
        RoomInn,
        key="The Harvest Moon",
        attributes=[
            ("desc",
             "Warm light from oil lamps plays across scarred oak tables where "
             "travellers nurse ales and swap road stories. A stone fireplace "
             "dominates the west wall, its mantel lined with curios left by "
             "patrons over the years — a dented helm, a whalebone pipe, a "
             "glass bottle with something moving inside. The bar is polished "
             "to a deep shine from decades of elbows. The air is thick with "
             "woodsmoke, roasting meat, and the yeasty warmth of fresh bread "
             "from the bakery next door."),
            ("details", {
                "fireplace": (
                    "A broad stone fireplace set into the west wall, blackened "
                    "from years of use. The mantel is cluttered with oddities "
                    "left by travellers — a dented helm with a crossbow bolt "
                    "still lodged in it, a whalebone pipe, a glass bottle "
                    "containing something small and dark that seems to move "
                    "when you're not looking directly at it."
                ),
                "fire": (
                    "A broad stone fireplace set into the west wall, blackened "
                    "from years of use. The mantel is cluttered with oddities "
                    "left by travellers — a dented helm with a crossbow bolt "
                    "still lodged in it, a whalebone pipe, a glass bottle "
                    "containing something small and dark that seems to move "
                    "when you're not looking directly at it."
                ),
                "bar": (
                    "A long oak bar polished to a deep shine. Tankards hang "
                    "from hooks overhead, and behind it shelves hold bottles "
                    "of every description — local ales, imported wines, and "
                    "a few unlabelled bottles the bartender reaches for only "
                    "when asked by name."
                ),
                "bottle": (
                    "A small glass bottle on the mantel, sealed with wax. "
                    "Something dark shifts inside it. You could swear it "
                    "moved just then, but when you look directly at it, "
                    "it's perfectly still."
                ),
                "chandelier": (
                    "A heavy iron chandelier hangs from the central beam, "
                    "fitted with a dozen oil lamps that cast warm, steady "
                    "light across the common room. The chain it hangs from "
                    "is thick enough to moor a boat."
                ),
                "lamps": (
                    "Oil lamps are mounted on the walls and clustered on "
                    "the central chandelier, keeping the common room bright "
                    "and welcoming at all hours."
                ),
            }),
            ("always_lit", True),
        ],
    )

    # ── Goldencrust Bakery (Processing — flour+wood → bread) ─────────
    rooms["bakery"] = create_object(
        RoomProcessing,
        key="Goldencrust Bakery",
        attributes=[
            ("processing_type", "bakery"),
            ("process_cost", 1),
            ("recipes", [
                {"inputs": {2: 1, 6: 1}, "output": 3, "amount": 1, "cost": 1},
            ]),
            ("desc",
             "Heat rolls out of two massive brick ovens set into the back "
             "wall, their iron doors blackened and warped from years of use. "
             "Wooden racks hold loaves in various stages — pale dough rising "
             "under damp cloths, golden crusts cooling, dark rye still "
             "steaming. Flour dusts every surface. A worn counter separates "
             "the workspace from a small shopfront where a chalkboard lists "
             "the day's prices."),
            ("details", {
                "ovens": (
                    "Two deep brick ovens built into the back wall. The "
                    "firebricks glow orange at the back, and the iron doors "
                    "are hot enough to scorch at arm's length. A long wooden "
                    "paddle leans against the wall for sliding loaves in and out."
                ),
                "oven": (
                    "Two deep brick ovens built into the back wall. The "
                    "firebricks glow orange at the back, and the iron doors "
                    "are hot enough to scorch at arm's length. A long wooden "
                    "paddle leans against the wall for sliding loaves in and out."
                ),
                "chalkboard": (
                    "A slate chalkboard behind the counter says"
                    "NO CREDIT.' The 'no credit' is underlined twice."
                ),
            }),
        ],
    )

    # ── Old Hendricks Smithy (Crafting — smithy) ─────────────────────
    rooms["smithy"] = create_object(
        RoomCrafting,
        key="Old Hendricks Smithy",
        attributes=[
            ("crafting_type", "smithy"),
            ("mastery_level", 1),
            ("craft_cost", 2),
            ("desc",
             "The ring of hammer on anvil fills this low-ceilinged workshop. "
             "A coal forge glows against the far wall, its bellows breathing "
             "in slow rhythm. Iron tongs, swages, and fullers hang from a "
             "rack within arm's reach of the anvil — a scarred block of steel "
             "that looks like it's absorbed a lifetime of blows. Finished "
             "work hangs from the rafters: horseshoes, hinges, a few bronze "
             "blades. The air tastes of hot metal and coal dust."),
            ("details", {
                "anvil": (
                    "A massive steel anvil, its face pocked and scarred from "
                    "thousands of hammer strikes. The horn is worn smooth and "
                    "the hardy hole has been reamed out and sleeved at least "
                    "once. This anvil has seen more work than most smiths see "
                    "in a lifetime."
                ),
                "forge": (
                    "A stone-lined coal forge against the far wall. The fire "
                    "bed glows white at its heart, fed by leather bellows "
                    "mounted on a wooden frame. A water trough sits beside "
                    "it, its surface scummed with scale and quench oil."
                ),
            }),
        ],
    )

    # ── The Tanned Hide (Crafting — leathershop) ─────────────────────
    rooms["leathershop"] = create_object(
        RoomCrafting,
        key="The Tanned Hide",
        attributes=[
            ("crafting_type", "leathershop"),
            ("mastery_level", 2),  # MasteryLevel.SKILLED
            ("craft_cost", 4),
            ("desc",
             "The sharp smell of tanning chemicals and cured leather hits you "
             "at the door. Hides in various stages of preparation hang from "
             "the rafters — raw skins, scraped pelts, and finished leather "
             "supple enough to fold. Workbenches hold awls, needles, and "
             "cutting tools alongside half-finished boots, belts, and armour "
             "pieces. A bucket of dubbin sits warming by a small brazier."),
            ("details", {
                "hides": (
                    "Hides hang from hooks driven into the rafters. The raw "
                    "ones at the back are stiff and hairy. Further forward "
                    "they become progressively cleaner, softer, and more "
                    "supple — a visible record of the tanning process from "
                    "start to finish."
                ),
            }),
        ],
    )

    # ── Millholm Textiles (Crafting — tailor) ───────────────────────
    rooms["textiles"] = create_object(
        RoomCrafting,
        key="Millholm Textiles",
        attributes=[
            ("crafting_type", "tailor"),
            ("mastery_level", 2),  # MasteryLevel.SKILLED
            ("craft_cost", 3),
            ("desc",
             "Bolts of cloth line the walls in stacked rolls — rough canvas, "
             "plain cotton, dyed wool in blues and greens. Two spinning wheels "
             "sit near the window where the light is best, and a heavy loom "
             "takes up the back half of the shop, its shuttle resting mid-row. "
             "Scraps of fabric and loose threads cover the floor around a "
             "cutting table where shears and chalk lines mark out patterns."),
            ("details", {
                "loom": (
                    "A heavy wooden loom, its frame darkened with age and "
                    "oil. Threads of pale cotton are strung tight across the "
                    "warp, and a half-finished piece of cloth shows a simple "
                    "herringbone pattern. The shuttle rests in the middle of "
                    "a row, as if the weaver stepped away just a moment ago."
                ),
            }),
        ],
    )

    # ── Shrine of the First Harvest (Temple) ─────────────────────────
    rooms["shrine"] = create_object(
        RoomBase,
        key="Shrine of the First Harvest",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Candlelight flickers across stone walls carved with sheaves of "
             "wheat and clusters of fruit. The altar is a broad slab of "
             "granite, its surface worn smooth, scattered with offerings — "
             "a loaf of bread, a handful of grain, a clay jug of cider. The "
             "air smells of beeswax and dried herbs. Wooden pews face the "
             "altar, their seats polished by generations of the faithful. "
             "A narrow stone staircase in the corner leads up."),
            ("details", {
                "altar": (
                    "A broad granite slab, waist height, its edges rounded by "
                    "centuries of touch. Today's offerings include a fresh "
                    "loaf of bread, a clay jug, and a small posy of wildflowers "
                    "already beginning to wilt."
                ),
                "carvings": (
                    "The wall carvings show scenes of harvest and plenty — "
                    "farmers gathering wheat, orchards heavy with fruit, "
                    "cattle grazing in long grass. The style is old but "
                    "skilled, and the stone is worn smooth where people have "
                    "touched the carvings for luck over the years."
                ),
            }),
        ],
    )

    # ── Circle of the First Light (Mages Guild) ──────────────────────
    rooms["mages_guild"] = create_object(
        RoomBase,
        key="Circle of the First Light",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "The air hums. Not audibly — you feel it in your teeth, in the "
             "fine hairs on your arms. Arcane symbols are etched into the "
             "stone pillars that support a vaulted ceiling lost in shadow. "
             "Bookshelves cover every wall, crammed with leather-bound tomes "
             "and rolled scrolls. A few robed figures study at reading desks, "
             "ignoring visitors with practiced indifference. Something "
             "shimmers faintly in the corner of your vision, but when you "
             "look directly, there's nothing there."),
            ("details", {
                "symbols": (
                    "Arcane symbols etched deep into the stone pillars. Some "
                    "you almost recognise — circles within circles, angular "
                    "runes, what might be star charts. Others make your eyes "
                    "water if you stare too long."
                ),
                "books": (
                    "Hundreds of volumes crammed into every available shelf. "
                    "Most are bound in plain leather, but a few are chained "
                    "to their shelves, and one appears to be breathing."
                ),
                "bookshelves": (
                    "Hundreds of volumes crammed into every available shelf. "
                    "Most are bound in plain leather, but a few are chained "
                    "to their shelves, and one appears to be breathing."
                ),
            }),
        ],
    )

    # ── The Iron Company (Warriors Guild) ────────────────────────────
    rooms["warriors_guild"] = create_object(
        RoomBase,
        key="The Iron Company",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "The sharp crack of wooden practice swords echoes off stone "
             "walls. Training dummies stand in a row along the far wall, "
             "their straw guts spilling from countless cuts. Weapon racks "
             "hold real steel — swords, axes, maces — and a battered wooden "
             "board lists the names of the company's current members in "
             "order of rank. The floor is sawdust over flagstone, dark with "
             "old sweat."),
            ("details", {
                "board": (
                    "A wooden board mounted on the wall, listing names in "
                    "a column. At the top: 'Warlord Thane — Commander.' "
                    "Below: 'Sergeant Grimjaw — Drill Master.' The rest are "
                    "members of varying rank. A few names have been struck "
                    "through."
                ),
                "weapons": (
                    "A rack of real weapons — not practice gear. Iron swords "
                    "with leather-wrapped grips, a heavy mace, a battle axe "
                    "with a notched blade. These are working weapons, not "
                    "display pieces."
                ),
                "rack": (
                    "A rack of real weapons — not practice gear. Iron swords "
                    "with leather-wrapped grips, a heavy mace, a battle axe "
                    "with a notched blade. These are working weapons, not "
                    "display pieces."
                ),
            }),
        ],
    )

    # ── 3x3 Market Square ────────────────────────────────────────────
    #
    #  Layout (from above):
    #
    #       sq_nw         sq_n          sq_ne
    #       sq_w          sq_center     sq_e
    #       sq_sw         sq_s          sq_se
    #
    #  Middle row (sq_w, sq_center, sq_e) = Old Trade Way through square
    #  Middle column (sq_n, sq_center, sq_s) = NS local road
    #  sq_center = The Crossroads
    #

    rooms["sq_nw"] = create_object(
        RoomBase,
        key="Market Square - Northwest",
        attributes=[
            ("desc",
             "A large oak tree dominates this corner of the market square, "
             "its spreading branches shading wooden benches where old men "
             "argue over dice games. A weathered jobs board stands beside "
             "the inn door. The cobblestones here are cracked and lifted by "
             "the oak's roots, and fallen leaves gather in the gaps."),
            ("details", {
                "oak": (
                    "This ancient oak must be several hundred years old. Its "
                    "trunk is wider than two men standing abreast, and deep "
                    "initials and hearts have been carved into the bark over "
                    "the decades. The roots have buckled the cobblestones in "
                    "a wide circle around the base."
                ),
                "tree": (
                    "This ancient oak must be several hundred years old. Its "
                    "trunk is wider than two men standing abreast, and deep "
                    "initials and hearts have been carved into the bark over "
                    "the decades. The roots have buckled the cobblestones in "
                    "a wide circle around the base."
                ),
                "oak tree": (
                    "This ancient oak must be several hundred years old. Its "
                    "trunk is wider than two men standing abreast, and deep "
                    "initials and hearts have been carved into the bark over "
                    "the decades. The roots have buckled the cobblestones in "
                    "a wide circle around the base."
                ),
                "benches": (
                    "Wooden benches under the oak, worn smooth by decades of "
                    "use. Old men sit here most days, arguing about weather, "
                    "politics, and whose grandson is the bigger disappointment."
                ),
            }),
        ],
    )

    rooms["sq_n"] = create_object(
        RoomBase,
        key="Market Square - North",
        attributes=[
            ("desc",
             "The north side of the market square opens onto a smaller road "
             "that heads out of town. A few market stalls line the edge, "
             "selling eggs, cheese, and bundles of herbs. The cobblestones "
             "are cleaner here where the road narrows, swept by a fastidious "
             "shopkeeper. The road north leads past the last houses toward "
             "open countryside."),
            ("details", {
                "stalls": (
                    "Simple wooden stalls with canvas awnings, selling "
                    "everyday goods — a basket of brown eggs, wheels of hard "
                    "cheese, bundles of dried rosemary and thyme. Nothing "
                    "exotic, just the staples of a farming town."
                ),
            }),
        ],
    )

    rooms["sq_ne"] = create_object(
        RoomBase,
        key="Market Square - Northeast",
        attributes=[
            ("desc",
             "A broad stone fountain stands in this corner of the square, "
             "its three tiers of worn basins overflowing with clear water "
             "that bubbles up from underground springs. Copper coins glint "
             "at the bottom — wishes cast by townsfolk and travellers. "
             "Citizens gather here to fill water jugs and exchange gossip."),
            ("details", {
                "fountain": (
                    "A broad stone fountain carved from a single block of "
                    "grey granite. Clear water bubbles up from underground "
                    "springs, cascading over three tiers of worn stone basins. "
                    "Copper coins glint at the bottom — wishes cast by "
                    "townsfolk and travellers alike. The fountain's rim is "
                    "smooth from generations of people sitting here to rest."
                ),
                "coins": (
                    "Copper coins scattered across the bottom of the fountain "
                    "basin, green with verdigris. A few silver pieces glint "
                    "among them — someone wished for something expensive."
                ),
            }),
        ],
    )

    rooms["sq_w"] = create_object(
        RoomBase,
        key="Old Trade Way West",
        attributes=[
            ("desc",
             "The Old Trade Way enters the market square from the west, the "
             "cobblestones widening as the road opens into the broad space. "
             "The sounds of commerce grow louder — bartering voices, the "
             "clatter of handcarts, a child chasing a dog between the stalls. "
             "The smithy's heavy iron door is set into the building to the "
             "north, and the old abandoned house sits shuttered to the south."),
        ],
    )

    rooms["sq_center"] = create_object(
        RoomBase,
        key="The Crossroads",
        attributes=[
            ("desc",
             "The heart of Millholm, where the Old Trade Way crosses the "
             "north-south road. Foot traffic flows in all four directions — "
             "farmers heading to market, merchants hauling goods, children "
             "darting between legs. The cobblestones here are worn to a "
             "smooth shine from centuries of passing feet and wheels. A "
             "faded iron compass rose is set into the ground at the exact "
             "centre of the crossing."),
            ("details", {
                "compass": (
                    "An iron compass rose set flush into the cobblestones, "
                    "about three feet across. The cardinal points are marked "
                    "with letters in an old script, and the iron has been "
                    "worn smooth and dark by countless feet passing over it. "
                    "It must have been here since the road was first laid."
                ),
                "compass rose": (
                    "An iron compass rose set flush into the cobblestones, "
                    "about three feet across. The cardinal points are marked "
                    "with letters in an old script, and the iron has been "
                    "worn smooth and dark by countless feet passing over it. "
                    "It must have been here since the road was first laid."
                ),
            }),
        ],
    )

    rooms["sq_e"] = create_object(
        RoomBase,
        key="Old Trade Way East",
        attributes=[
            ("desc",
             "The trade road continues east from the crossroads, the square "
             "giving way to more modest buildings. The textile shop's "
             "colourful window display brightens the north side of the road, "
             "while the imposing bronze door of the bank dominates the south. "
             "Beyond, the road narrows as it heads toward the edge of town."),
        ],
    )

    rooms["sq_sw"] = create_object(
        RoomBase,
        key="Market Square - Southwest",
        attributes=[
            ("desc",
             "A weathered stone monument stands in this corner of the square, "
             "commemorating Millholm's founding. Fresh flowers at its base "
             "suggest someone still tends the memorial. The ornate doors of "
             "the Shrine of the First Harvest face the monument from the "
             "south, and the general store's shopfront opens to the west."),
            ("details", {
                "monument": (
                    "A stone monument about eight feet tall, carved from local "
                    "granite. Bronze plaques at its base tell the story of "
                    "Millholm's founding: how a dwarven miller and a halfling "
                    "farmer established a settlement where the river met the "
                    "trade road. The names of the founding families are listed "
                    "below — Stonefield, Brightwater, Goldwheat, and Ironhand. "
                    "Fresh flowers suggest someone still tends the memorial."
                ),
                "flowers": (
                    "A small posy of wildflowers laid at the base of the "
                    "monument. They're fresh — placed this morning, perhaps. "
                    "Someone in Millholm still remembers the founders."
                ),
                "plaques": (
                    "Bronze plaques set into the granite base, green with age. "
                    "They name the founding families — Stonefield, Brightwater, "
                    "Goldwheat, and Ironhand — and tell how a dwarven miller "
                    "and a halfling farmer built the first buildings where "
                    "the river met the trade road."
                ),
            }),
        ],
    )

    rooms["sq_s"] = create_object(
        RoomBase,
        key="Market Square - South",
        attributes=[
            ("desc",
             "The south side of the market square narrows into a road that "
             "leads deeper into the southern reaches of Millholm. The "
             "buildings here are more tightly packed, the road shaded by "
             "upper storeys that lean toward each other overhead. The alchemist's "
             "door is set into a crooked building to the west, its sign "
             "depicting a mortar and pestle."),
        ],
    )

    rooms["sq_se"] = create_object(
        RoomBase,
        key="Market Square - Southeast",
        attributes=[
            ("desc",
             "The southeast corner of the square serves as an informal "
             "marketplace where farmers and craftsmen set up temporary "
             "stalls. Wooden crates and barrels are stacked against the "
             "wall, and the smell of fresh produce mingles with the sounds "
             "of bartering. The warriors' guild and the mages' hall face "
             "each other across this busy corner."),
            ("details", {
                "stalls": (
                    "Temporary wooden stalls with oilcloth canopies. A farmer "
                    "sells turnips and cabbages from a handcart. A woman "
                    "offers baskets of dried mushrooms. A boy hawks meat pies "
                    "from a tray, shouting that they're still hot."
                ),
                "crates": (
                    "Stacked wooden crates stamped with merchant marks. Some "
                    "are open, showing straw packing around pottery and "
                    "glassware. Others are nailed shut, bound for destinations "
                    "further along the trade road."
                ),
            }),
        ],
    )

    # ── Residential houses ───────────────────────────────────────────
    rooms["hendricks_house"] = create_object(
        RoomBase,
        key="Old Hendricks House",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A small room behind the smithy, thick with the smell of coal "
             "smoke that seeps through the shared wall. A narrow bed, a "
             "wooden chest, and a washbasin with a cracked mirror. Tools and "
             "metalworking references are scattered about — even here, the "
             "craft follows the man."),
        ],
    )

    rooms["gareth_house"] = create_object(
        RoomBase,
        key="Gareth Stonefield's House",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A well-maintained home with quality furniture that speaks to "
             "its owner's success in trade. Maps and ledgers cover the desk, "
             "and a lockbox sits beneath it. The bookshelves hold an "
             "impressive collection of leather-bound volumes on trade, "
             "economics, and geography. A narrow wooden staircase in the "
             "corner leads up to the first floor."),
            ("details", {
                "maps": (
                    "Trade maps showing routes across the continent — "
                    "Millholm to Ironback Peaks, Millholm to the coast. "
                    "Distances and travel times are annotated in a precise "
                    "hand. Some routes have been crossed out and redrawn."
                ),
                "bookcase": (
                    "An impressive bookcase housing leather-bound tomes on "
                    "trade, economics, and geography. The collection is "
                    "unusually large for a merchant in a farming town."
                ),
                "staircase": (
                    "A narrow wooden staircase, well-polished from use, "
                    "spirals tightly upward to the first floor. The treads "
                    "are worn smooth in the centre."
                ),
            }),
        ],
    )

    rooms["gareth_bedroom"] = create_object(
        RoomBase,
        key="Gareth's Bedroom",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A modest but comfortable bedroom tucked under the eaves of "
             "the house. A heavy oak bed with clean linen dominates the "
             "room, and a washstand and mirror occupy one corner. A "
             "battered sea chest sits at the foot of the bed, secured "
             "with a brass padlock. A large oak wardrobe stands against "
             "the far wall, slightly too big for the room. The ceiling "
             "slopes sharply on one side, following the line of the "
             "roof. A small window looks out over the rooftops of the "
             "craft quarter."),
            ("details", {
                "chest": (
                    "A battered sea chest, the kind used by sailors. It's "
                    "out of place in a merchant's bedroom. The brass "
                    "padlock is heavy and well-oiled."
                ),
                "window": (
                    "A small window set into the sloping wall, looking "
                    "out over the rooftops of the craft quarter. The "
                    "slate tiles of the neighbouring workshops stretch "
                    "away below. The window is hinged and looks like it "
                    "could be opened."
                ),
                "bed": (
                    "A sturdy oak bed frame with a horsehair mattress "
                    "and clean linen. The pillows are plump. Gareth "
                    "clearly values his sleep."
                ),
                "wardrobe": (
                    "A massive oak wardrobe, dark with age and polish. "
                    "It's slightly too large for the room — as if it "
                    "was built here rather than carried up the stairs. "
                    "The doors hang slightly open, revealing a few "
                    "cloaks and a heavy winter coat. There are scuff "
                    "marks on the floorboards around its base."
                ),
            }),
        ],
    )

    rooms["mara_house"] = create_object(
        RoomBase,
        key="Mara Brightwater's House",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Dried plants hang from every rafter — bundles of herbs, flower "
             "heads, roots strung on twine. Shelves hold jars of powders and "
             "tinctures in colours that shouldn't exist in nature. The air "
             "is a complex mixture of herbal scents, some familiar, some "
             "unsettling. A cat watches you from atop a stack of almanacs."),
            ("details", {
                "cat": (
                    "A large grey cat with unsettling green eyes. It watches "
                    "you without blinking from atop a stack of almanacs, its "
                    "tail curled neatly around its paws. It does not look "
                    "like it wants to be petted."
                ),
                "jars": (
                    "Glass jars of every size, filled with powders, dried "
                    "leaves, seeds, and things you'd rather not identify. "
                    "The labels are written in a cramped hand — some in "
                    "Common, some in symbols you don't recognise."
                ),
            }),
        ],
    )

    rooms["elena_house"] = create_object(
        RoomBase,
        key="Elena Copperkettle's House",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Fabric samples, thread spools, and sewing implements are "
             "organized with surprising precision for a home this cluttered. "
             "Half-finished garments hang on wooden forms, and a large loom "
             "dominates one corner. A kettle sits perpetually warm on the "
             "stove — Elena is always ready for visitors and gossip."),
        ],
    )

    # ── The Old Trade Way (approaching and leaving town) ─────────────

    rooms["road_far_west"] = create_object(
        RoomBase,
        key="Old Trade Way West",
        attributes=[
            ("desc",
             "The trade road stretches westward, leaving the last buildings "
             "of Millholm behind. Rolling farmland opens up ahead, golden "
             "wheat fields and grazing livestock visible in the distance. "
             "A weathered signpost marks the town boundary."),
            ("details", {
                "signpost": (
                    "A weathered wooden signpost. One arm reads 'Millholm' "
                    "pointing east, the other 'Farms' pointing west. Bird "
                    "droppings streak the top."
                ),
                "sign": (
                    "A weathered wooden signpost. One arm reads 'Millholm' "
                    "pointing east, the other 'Farms' pointing west. Bird "
                    "droppings streak the top."
                ),
            }),
        ],
    )

    rooms["road_west"] = create_object(
        RoomBase,
        key="Old Trade Way West",
        attributes=[
            ("desc",
             "The trade road approaches town from the west, packed earth "
             "giving way to cobblestones. The smell of woodsmoke and cooking "
             "food drifts on the breeze, and the sounds of daily commerce "
             "grow stronger ahead. The woodshop's sign is visible to the "
             "north, its carved oak leaf swinging gently."),
        ],
    )

    rooms["road_east"] = create_object(
        RoomBase,
        key="Old Trade Way East",
        attributes=[
            ("desc",
             "The road narrows as it leaves the square behind, heading east "
             "toward the edge of town. The buildings become sparser and more "
             "utilitarian — storage sheds and workshops that don't need to "
             "attract customers. The air carries the faint smell of sawdust "
             "and hot metal from somewhere ahead."),
        ],
    )

    rooms["road_far_east"] = create_object(
        RoomBase,
        key="Old Trade Way East",
        attributes=[
            ("desc",
             "The cobblestones end here, giving way to packed earth as the "
             "road heads east. The noise and smell of industry grows stronger "
             "— the rhythmic shriek of the sawmill and the heat-shimmer of "
             "the smelter are visible ahead. Beyond the industrial buildings, "
             "the treeline of the woods rises dark against the sky."),
        ],
    )

    # ── North Road and Cemetery ──────────────────────────────────────

    rooms["north_road"] = create_object(
        RoomBase,
        key="North Road",
        attributes=[
            ("desc",
             "A quiet road leading north from the market square, lined with "
             "the last few houses before the town gives way to open ground. "
             "Wildflowers grow in the verges, and the road is less worn than "
             "the busy trade way — fewer carts pass this way. A dirt track "
             "branches west toward wrought-iron gates, and the road continues "
             "north into open countryside."),
        ],
    )


    # ── South Road (extends south from sq_s to south gate) ──────────

    rooms["south_road"] = create_object(
        RoomBase,
        key="South Road",
        attributes=[
            ("desc",
             "The road south from the market square narrows between "
             "close-packed buildings, their upper storeys leaning inward "
             "until the sky is just a strip overhead. The cobblestones are "
             "slick with runoff from the eaves. The air is cooler here, "
             "shaded and slightly damp. The road continues south into parts "
             "of Millholm you haven't explored yet."),
        ],
    )

    rooms["mid_south_road"] = create_object(
        RoomBase,
        key="South Road",
        attributes=[
            ("desc",
             "The road continues south between tightly-packed buildings. "
             "The guild halls and respectable shops of the square have "
             "given way to sturdier, plainer structures — a training yard "
             "echoes with the clash of practice weapons to the east, while "
             "a narrow alley opens to the west, reeking of cheap wine and "
             "desperation."),
        ],
    )

    rooms["far_south_road"] = create_object(
        RoomBase,
        key="South Road",
        attributes=[
            ("desc",
             "The road widens slightly as it approaches the town's "
             "southern boundary. The buildings here are rougher — "
             "patched roofs, shuttered windows, and the kind of quiet "
             "that comes from people minding their own business. A "
             "battered tavern sign creaks to the west. The town wall "
             "and south gate are visible ahead."),
        ],
    )

    rooms["upper_south_road"] = create_object(
        RoomBase,
        key="South Road",
        attributes=[
            ("desc",
             "The road passes between the backs of guild halls to the "
             "north and the workshops of Artisan's Way to the south. "
             "The walls on either side are plain and functional — no "
             "shopfronts face this stretch, just service doors and "
             "barred windows. The sound of hammers and the smell of "
             "hot metal drift from the lane to the south."),
        ],
    )

    rooms["lower_south_road"] = create_object(
        RoomBase,
        key="South Road",
        attributes=[
            ("desc",
             "A quieter stretch of road between Artisan's Way and the "
             "rougher end of town. The workshops to the north give way "
             "to residential buildings to the south — smaller, plainer, "
             "with window boxes instead of shop signs. A cat watches "
             "you from a windowsill with studied indifference."),
        ],
    )

    # ── Artisan's Way (junction + east-west lane) ─────────────────
    rooms["artisans_way"] = create_object(
        RoomBase,
        key="Artisan's Way",
        attributes=[
            ("desc",
             "A cobbled lane branches east and west from the main road, "
             "narrower than the Trade Way but busy with a different kind "
             "of commerce. The ring of hammers, the rasp of saws, and the "
             "sharp smell of tanning chemicals fill the air. Hand-painted "
             "signs hang above workshop doors in both directions. This is "
             "where Millholm's craftsmen ply their trades, away from the "
             "bustle of the market square."),
        ],
    )

    rooms["artisans_way_w1"] = create_object(
        RoomBase,
        key="Artisan's Way",
        attributes=[
            ("desc",
             "The western stretch of Artisan's Way. Workshop doors line "
             "both sides of the narrow lane. The clatter of a loom sounds "
             "from behind one door, while the steady tap of a jeweller's "
             "hammer comes from another."),
            ("max_height", 2),
        ],
    )

    rooms["artisans_way_w2"] = create_object(
        RoomBase,
        key="Artisan's Way",
        attributes=[
            ("desc",
             "The lane continues west past soot-stained walls. The air "
             "here is thick with the heat of forges and the acrid bite "
             "of hot metal. Iron filings crunch underfoot."),
        ],
    )

    rooms["artisans_way_w3"] = create_object(
        RoomBase,
        key="Artisan's Way",
        attributes=[
            ("desc",
             "The western end of Artisan's Way. Wood shavings carpet "
             "the cobblestones and the sweet smell of fresh-cut timber "
             "hangs in the air. A large workshop dominates the dead end."),
        ],
    )

    rooms["artisans_way_e1"] = create_object(
        RoomBase,
        key="Artisan's Way",
        attributes=[
            ("desc",
             "The eastern stretch of Artisan's Way. Dried herbs hang "
             "from hooks above doorways and the air carries a complex "
             "bouquet of medicinal scents — camphor, lavender, and "
             "something sharper underneath."),
        ],
    )

    rooms["artisans_way_e2"] = create_object(
        RoomBase,
        key="Artisan's Way",
        attributes=[
            ("desc",
             "The lane narrows further to the east. A jeweller's loupe "
             "sign creaks above one doorway. The cobblestones here are "
             "cleaner, swept regularly by fastidious craftsmen."),
        ],
    )

    rooms["artisans_way_e3"] = create_object(
        RoomBase,
        key="Artisan's Way",
        attributes=[
            ("desc",
             "The eastern dead end of Artisan's Way. The sharp chemical "
             "smell of tanning solution is unmistakable here. Hides hang "
             "on wooden frames outside one of the workshops, drying in "
             "the air."),
        ],
    )

    # ── Vacant workshops (future expansion slots) ──────────────────
    rooms["vacant_w1"] = create_object(
        RoomBase,
        key="Vacant Workshop",
        attributes=[
            ("desc",
             "A shuttered workshop with a faded 'To Let' sign nailed "
             "to the door. Cobwebs fill the windows and dust coats every "
             "surface. Whatever trade was practiced here has moved on, "
             "leaving only the ghost of industry behind. At the back of "
             "the room, a sheet of corrugated iron leans against the "
             "wall, slightly askew."),
            ("details", {
                "corrugated iron": (
                    "A large sheet of rusted corrugated iron propped "
                    "against the back wall. It doesn't quite sit flush — "
                    "there's a draught coming from behind it, and scuff "
                    "marks on the floor suggest it's been moved recently."
                ),
                "iron": (
                    "A large sheet of rusted corrugated iron propped "
                    "against the back wall. It doesn't quite sit flush — "
                    "there's a draught coming from behind it, and scuff "
                    "marks on the floor suggest it's been moved recently."
                ),
                "scuff marks": (
                    "The dust on the floor has been disturbed in an arc, "
                    "as if something heavy has been swung aside repeatedly."
                ),
            }),
        ],
    )

    rooms["back_alley"] = create_object(
        RoomBase,
        key="Back Alley",
        attributes=[
            ("desc",
             "A narrow, stinking alley squeezed between the backs of "
             "workshops. Damp brick walls rise high on either side, "
             "streaked with soot and moss. Broken crates and refuse are "
             "piled against one wall. A rusted iron drainpipe runs up "
             "the side of the old workshop to the rooftops above — it "
             "looks climbable, if you don't mind the height."),
            ("max_height", 1),
            ("details", {
                "drainpipe": (
                    "A thick iron drainpipe bolted to the brickwork, "
                    "running from the cobbles all the way up to the "
                    "guttering. The bolts are rusted but solid. Someone "
                    "has wrapped rags around the pipe at intervals — "
                    "handholds. This has been climbed before."
                ),
                "pipe": (
                    "A thick iron drainpipe bolted to the brickwork, "
                    "running from the cobbles all the way up to the "
                    "guttering. The bolts are rusted but solid. Someone "
                    "has wrapped rags around the pipe at intervals — "
                    "handholds. This has been climbed before."
                ),
                "crates": (
                    "Splintered wooden crates, mostly empty. A few still "
                    "hold mouldy straw and the faint smell of turpentine."
                ),
                "refuse": (
                    "A heap of rotten vegetable peelings, broken pottery, "
                    "and things you'd rather not examine too closely."
                ),
            }),
        ],
    )

    rooms["vacant_w2"] = create_object(
        RoomBase,
        key="Vacant Workshop",
        attributes=[
            ("desc",
             "An empty workshop, its chimney cold and doorway boarded. "
             "Soot stains on the stonework suggest a forge once burned "
             "here. A 'For Let — Inquire at Town Hall' notice is pinned "
             "to the boards."),
        ],
    )

    rooms["vacant_e2"] = create_object(
        RoomBase,
        key="Vacant Workshop",
        attributes=[
            ("desc",
             "A disused workshop at the far end of the lane. The door "
             "hangs slightly ajar, revealing an empty room with bare "
             "shelves and a cold hearth. A faded sign reads 'Workshop "
             "Available — Good Terms for Honest Trade.'"),
        ],
    )

    rooms["south_gate"] = create_object(
        RoomBase,
        key="South Gate",
        attributes=[
            ("desc",
             "The southern wall of Millholm rises here — ten feet of "
             "rough stone topped with wooden palisades, built more to "
             "keep wildlife out than to withstand a siege. A wide gate "
             "of iron-banded oak stands open, flanked by squat guard "
             "towers. Beyond the gate, open countryside stretches south "
             "under a wide sky. The guards here look more alert than "
             "their counterparts elsewhere in town — whatever is out "
             "there, they take it seriously."),
        ],
    )
    rooms["south_gate"].details = {
        "wall": (
            "Rough fieldstone mortared with lime, patched in places "
            "with timber and packed earth. Not a proper fortification "
            "— more of a boundary marker with pretensions. But the "
            "palisade on top adds another four feet, and the guard "
            "towers give a clear line of sight across the southern "
            "approaches."
        ),
        "guards": (
            "Two guards in leather armour with crossbows racked "
            "within easy reach. They check travellers entering the "
            "town but wave most people through with a nod. Their eyes "
            "keep drifting south — watching the grasslands."
        ),
        "gate": (
            "Heavy oak planks banded with iron, hung on massive hinges. "
            "The gate stands open during the day but is barred at night. "
            "Deep grooves in the cobblestones show where it swings."
        ),
    }

    rooms["broken_crown"] = create_object(
        RoomBase,
        key="The Broken Crown",
        attributes=[
            ("desc",
             "A low-ceilinged tavern that smells of spilled ale, pipe "
             "smoke, and trouble. The furniture is heavy and scarred, "
             "bolted to the floor to discourage its use as weaponry. "
             "A cracked wooden crown hangs above the bar — the tavern's "
             "namesake, supposedly looted from a baron's estate three "
             "counties over. The clientele are the kind who drink in "
             "the afternoon and mind their own business. A fireplace "
             "gives off more smoke than heat."),
        ],
    )
    rooms["broken_crown"].details = {
        "crown": (
            "A wooden crown, gilded once but now flaking and cracked "
            "down the middle. Whether the story about the baron is true "
            "or not, the crown has been hanging here longer than anyone "
            "can remember."
        ),
        "clientele": (
            "Off-duty labourers, out-of-work mercenaries, and people "
            "who prefer not to give their names. Conversations are "
            "conducted in low voices, and strangers who ask too many "
            "questions tend to leave with fewer teeth."
        ),
        "fireplace": (
            "The chimney draws poorly, filling the room with a haze "
            "of woodsmoke that stings the eyes. Nobody seems to mind "
            "— or maybe nobody wants to pay for a sweep."
        ),
    }

    rooms["gaol"] = create_object(
        RoomBase,
        key="Millholm Gaol",
        attributes=[
            ("desc",
             "A squat stone building with barred windows and a heavy "
             "iron-banded door. Inside, a narrow corridor runs between "
             "two rows of cells, most empty but a few occupied by "
             "sullen figures who watch you pass with hollow eyes. The "
             "air is damp and cold, thick with the smell of unwashed "
             "bodies and old straw. A bored guard sits at a desk near "
             "the entrance, scratching tallies into a ledger."),
        ],
    )
    rooms["gaol"].details = {
        "cells": (
            "Iron bars set into stone, with straw pallets and wooden "
            "buckets for furnishing. The occupied cells hold petty "
            "thieves and drunks, mostly — the real criminals in "
            "Millholm don't get caught."
        ),
        "guard": (
            "A heavyset man in a stained tabard, more interested in "
            "his ledger than in you. He has the look of someone who "
            "has been doing this job for too long and stopped caring "
            "about it years ago."
        ),
    }

    rooms["gaol_cell"] = create_object(
        RoomBase,
        key="Gaol Cell",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A cramped stone cell barely six feet wide, its walls "
             "scratched with tally marks, crude drawings, and the "
             "occasional desperate prayer. A thin straw pallet lies "
             "on the floor, stained with things you'd rather not "
             "think about. A wooden bucket in the corner serves as "
             "the sole amenity. Daylight creeps in through a barred "
             "window high on the wall — just enough to see by, just "
             "enough to remind you of what you're missing. Someone "
             "has carved 'TIMMY WOZ ERE' into the stone above the "
             "pallet, and beneath it, in different handwriting, 'SO "
             "WOZ 'IS MUM — 3 TIMES'."),
            ("details", {
                "tally marks": (
                    "Hundreds of scratched lines covering one wall, "
                    "grouped in fives. Someone spent a long time in "
                    "here. The marks start neat and even near the "
                    "door and become increasingly frantic toward the "
                    "corner."
                ),
                "pallet": (
                    "A thin straw pallet, flattened by the weight of "
                    "many previous occupants. It smells of old sweat "
                    "and regret. A single flea hops lazily across "
                    "the surface."
                ),
                "bucket": (
                    "A wooden bucket. You don't need to look more "
                    "closely. You really don't."
                ),
                "window": (
                    "A small barred window high on the wall. Through "
                    "it you can see a sliver of sky and hear the "
                    "distant sounds of the town going about its "
                    "business without you."
                ),
                "carvings": (
                    "'TIMMY WOZ ERE' — carved with something sharp, "
                    "probably a smuggled nail. Below it: 'SO WOZ 'IS "
                    "MUM — 3 TIMES'. Below that, in tiny letters: "
                    "'Timmy's mum is innocent (she told me so)'. "
                    "Timmy appears to be a recurring figure in "
                    "Millholm's history of minor catastrophe."
                ),
            }),
        ],
    )

    rooms["beggars_alley"] = create_object(
        RoomBase,
        key="Beggar's Alley",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("quest_tags", ["cleric_initiation"]),
            ("desc",
             "A narrow, stinking alley wedged between two sagging "
             "buildings. Threadbare blankets and scraps of canvas form "
             "makeshift shelters along the walls. A few gaunt figures "
             "huddle in doorways, watching passersby with dull eyes. "
             "The cobblestones are slick with refuse, and the air is "
             "thick with the smell of unwashed bodies and rotting food. "
             "Even the rats look underfed."),
        ],
    )

    # ── The Old Trade Way — new mid-road segments ──────────────────

    rooms["road_mid_west"] = create_object(
        RoomBase,
        key="Old Trade Way West",
        attributes=[
            ("desc",
             "The trade road passes between a cluster of workshops and "
             "homes. The rhythmic clang of a hammer on metal rings out "
             "from a smithy to the north, its chimney sending a column "
             "of dark smoke into the sky. A boarded-up building stands "
             "to the south, its windows dark and its door sealed shut."),
        ],
    )

    rooms["road_mid_east"] = create_object(
        RoomBase,
        key="Old Trade Way East",
        attributes=[
            ("desc",
             "The trade road continues east past quieter establishments. "
             "The sharp, herbal smell of an apothecary drifts from the "
             "north, while a modest stone building to the south bears "
             "the sign of the Millholm Post — a quill crossed with a "
             "sealed letter."),
        ],
    )

    # ── New buildings ──────────────────────────────────────────────

    rooms["post_office"] = create_object(
        RoomPostOffice,
        key="Millholm Post Office",
        attributes=[
            ("desc",
             "A tidy stone building with a polished wooden counter "
             "dividing the public area from the sorting room behind. "
             "Cubbyholes line the back wall, stuffed with letters and "
             "small parcels. A clerk in a neat waistcoat stamps and "
             "sorts with practised efficiency. A board on the wall "
             "lists the services available."),
            ("details", {
                "board": (
                    "A neatly lettered board reads:\n"
                    "  |wPOSTAL SERVICES|n\n"
                    "  |wmail|n                — view your inbox\n"
                    "  |wmail|n |c<#>|n              — read a message\n"
                    "  |wmail|n |c<name>|n=|c<subject>/<body>|n — send mail\n"
                    "  |wmail reply|n |c<#>|n=|c<message>|n  — reply\n"
                    "  |wmail delete|n |c<#>|n         — delete a message"
                ),
                "clerk": (
                    "A thin man with wire-rimmed spectacles and ink-"
                    "stained fingers. He handles each letter with the "
                    "care of someone who takes his work very seriously."
                ),
            }),
        ],
    )

    rooms["distillery"] = create_object(
        RoomProcessing,
        key="Millholm Distillery",
        attributes=[
            ("processing_type", "distillery"),
            ("process_cost", 3),
            ("recipes", [
                {"inputs": {12: 1}, "output": 13, "amount": 1, "cost": 3},
            ]),
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "The air inside is thick with the sweet, heady smell of "
             "fermenting grain and juniper. Copper stills gleam in the "
             "firelight, their coiled tubes dripping clear liquid into "
             "collecting jars. Barrels in various stages of aging line "
             "the walls, chalked with dates and cryptic initials. The "
             "distiller, a broad woman with copper-red hair and a "
             "permanent flush, tends her apparatus with a chemist's "
             "precision."),
            ("details", {
                "stills": (
                    "Beautiful copper constructions, lovingly polished "
                    "and meticulously maintained. The largest is named "
                    "'Old Bess' — scratched into the copper in an "
                    "elegant hand."
                ),
                "barrels": (
                    "Oak barrels of various sizes, stacked and racked. "
                    "The chalk marks record dates going back years. "
                    "Some of the oldest barrels have a reverent 'DO NOT "
                    "TOUCH' scrawled across them."
                ),
            }),
        ],
    )

    # ── Jeweller ────────────────────────────────────────────────────
    rooms["jeweller"] = create_object(
        RoomCrafting,
        key="The Gilded Setting",
        attributes=[
            ("crafting_type", "jeweller"),
            ("mastery_level", 1),
            ("craft_cost", 5),
            ("desc",
             "A small, immaculate workshop lit by dozens of candles and "
             "a magnifying lens on an articulated brass arm. Velvet-lined "
             "trays hold gems sorted by colour and cut — rubies, emeralds, "
             "sapphires, and a single diamond that catches every flicker "
             "of light. Silver and copper ingots are stacked on a shelf "
             "beside delicate tools: tiny hammers, pliers, files, and "
             "setting jigs. The jeweller works in focused silence, a "
             "loupe clamped to one eye."),
            ("details", {
                "gems": (
                    "Dozens of cut stones arranged on velvet trays, each "
                    "in its own shallow depression. The rubies glow like "
                    "embers, the emeralds like deep water. A few uncut "
                    "stones sit in a separate tray, rough and unassuming."
                ),
                "tools": (
                    "Miniature hammers, needle-nosed pliers, files no "
                    "thicker than a quill, and brass setting jigs for "
                    "every ring and pendant size. Everything is arranged "
                    "with obsessive precision."
                ),
            }),
        ],
    )

    # ── Stables ──────────────────────────────────────────────────────
    rooms["stables"] = create_object(
        RoomBase,
        key="Millholm Stables",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Straw-floored stalls line both sides of this large timber "
             "building. A few horses doze in their boxes, tails flicking "
             "at flies. The smell of hay, leather tack, and warm animal "
             "fills the air. Saddles and bridles hang from hooks on the "
             "central post, and a stable hand forks fresh bedding into "
             "an empty stall."),
            ("details", {
                "horses": (
                    "A few horses stand in their stalls — a heavy draught "
                    "horse with feathered hooves, a compact bay pony, and a "
                    "chestnut mare that watches you with intelligent eyes. "
                    "They're well-fed and well-groomed."
                ),
            }),
        ],
    )

    # ── Inn interior — vertical chain ────────────────────────────────
    rooms["stairwell"] = create_object(
        RoomBase,
        key="Stairwell",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A narrow stone stairwell behind the inn's main room. Worn "
             "steps show the passage of countless feet, and iron handrails "
             "offer support. Torches in wall sconces provide flickering "
             "light. Steps lead both up and down from here."),
        ],
    )

    rooms["cellar_stairwell"] = create_object(
        RoomBase,
        key="Cellar Stairwell",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Steep stone steps descend into cooler, damper air. Moss clings "
             "to the walls and the sound of dripping water echoes from "
             "somewhere below. A musty smell of earth and age rises from "
             "the depths."),
        ],
    )

    rooms["first_floor_stairwell"] = create_object(
        RoomBase,
        key="First Floor Stairwell",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "The upper stairwell is better maintained — polished wooden "
             "steps and brass handrails. A window set high in the wall "
             "lets in natural light. The hallway continues south to the "
             "guest rooms."),
        ],
    )

    rooms["cellar"] = create_object(
        RoomBase,
        key="Cellar",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A cool, dark cellar beneath The Harvest Moon. Barrels of ale "
             "and casks of wine line the rough stone walls. Crates of dried "
             "goods are stacked in the corners. The yeasty aroma of "
             "fermenting brew mingles with the earthy smell of underground "
             "stone. Water drips steadily from somewhere in the shadows, "
             "and the ceiling creaks with the footsteps of patrons above."),
            ("details", {
                "barrels": (
                    "Oak barrels of various sizes, their staves dark with "
                    "age. Chalk marks on the ends identify the contents — "
                    "'Pale', 'Stout', 'Cider', and one that just says 'NO' "
                    "in large letters."
                ),
            }),
        ],
    )

    rooms["back_cellar"] = create_object(
        RoomBase,
        key="Back Cellar",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A narrow extension of the cellar, darker and damper than "
             "the main room. Old crates and broken furniture are piled "
             "against the walls. The air is still and musty. Whatever "
             "was down here has been cleared out — only gnaw marks on "
             "the crates and a few scattered droppings remain as evidence."),
        ],
    )

    rooms["hallway"] = create_object(
        RoomBase,
        key="Upstairs Hallway",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A narrow hallway across the upper floor. Polished wooden "
             "boards creak softly underfoot. Oil lamps on the walls provide "
             "warm light, and doors lead to guest rooms on either side. A "
             "window at the far end offers a view of the market square below."),
        ],
    )

    rooms["bedroom_east"] = create_object(
        RoomBase,
        key="Bedroom",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A cozy guest room with a comfortable bed, a wooden wardrobe, "
             "and a small writing desk near the window. Morning sunlight "
             "streams in from the east, and the sounds of the market square "
             "drift up from below."),
        ],
    )

    rooms["bedroom_west"] = create_object(
        RoomBase,
        key="Bedroom",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A peaceful guest room overlooking the western approaches to "
             "town. A well-made bed, a chest of drawers, and a reading "
             "chair by the window. The view of the trade road and "
             "countryside beyond makes this the room to watch the sunset."),
        ],
    )

    # ── Guild back rooms ─────────────────────────────────────────────
    rooms["barracks"] = create_object(
        RoomBase,
        key="Barracks",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Simple wooden bunks line the walls, each with a small chest "
             "for personal belongings. Weapon racks hold spears and "
             "crossbows. A table in the centre serves for meals and "
             "briefings. The room is kept clean and orderly — military "
             "discipline, even in a farming town."),
        ],
    )

    rooms["priest_quarters"] = create_object(
        RoomBase,
        key="Priest's Quarters",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A modest chamber above the shrine, reached by a narrow stone "
             "staircase. A simple bed, a prayer desk worn smooth at the "
             "kneeling rail, shelves of religious texts. Candles provide "
             "gentle light. The atmosphere is peaceful, thick with the scent "
             "of old incense and beeswax."),
        ],
    )

    rooms["arcane_study"] = create_object(
        RoomCrafting,
        key="Arcane Study",
        attributes=[
            ("crafting_type", "enchanting"),
            ("mastery_level", 1),
            ("craft_cost", 2),
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A private chamber crammed with the tools of magical research. "
             "Towering bookshelves, a desk buried in notes and quills, "
             "crystal orbs on iron stands, and apparatus whose purpose is "
             "unclear. The air shimmers occasionally. Arcane symbols on the "
             "walls pulse faintly if you look at them from the corner of "
             "your eye. Against the far wall stands a runescribed slab of "
             "dark stone — the guild's binding plinth, its surface etched "
             "with concentric circles that glow faintly."),
            ("details", {
                "plinth": (
                    "A waist-high slab of polished obsidian, its flat surface "
                    "carved with concentric rings of tiny runes. The innermost "
                    "circle is just large enough to place a weapon or piece of "
                    "armour. Faint light pulses through the carvings like a slow "
                    "heartbeat — the stone is never quite still. This is where "
                    "enchantments are bound to physical objects."
                ),
                "binding plinth": (
                    "A waist-high slab of polished obsidian, its flat surface "
                    "carved with concentric rings of tiny runes. The innermost "
                    "circle is just large enough to place a weapon or piece of "
                    "armour. Faint light pulses through the carvings like a slow "
                    "heartbeat — the stone is never quite still. This is where "
                    "enchantments are bound to physical objects."
                ),
            }),
        ],
    )

    # ── The Mortar and Pestle (Crafting — apothecary) ────────────────
    rooms["apothecary"] = create_object(
        RoomCrafting,
        key="The Mortar and Pestle",
        attributes=[
            ("crafting_type", "apothecary"),
            ("mastery_level", 1),
            ("craft_cost", 6),
            ("desc",
             "Glass vials and beakers crowd every surface, some bubbling "
             "over spirit lamps, others sitting still and dark. Dried herbs "
             "hang from the rafters in dense bundles, and the air is thick "
             "with competing scents — mint, sulphur, something floral, "
             "something that burns the back of your throat. Mortar and "
             "pestle sets of different sizes sit ready for grinding."),
            ("details", {
                "vials": (
                    "Glass vials in every size, some clear, some coloured. "
                    "A few contain liquids that glow faintly in the dim "
                    "light. Labels in a cramped hand identify contents — "
                    "'Healing (minor)', 'Sleep', 'DO NOT DRINK'."
                ),
            }),
        ],
    )

    # ── Order of the Golden Scale (Bank) ─────────────────────────────
    rooms["bank"] = create_object(
        RoomBank,
        key="Order of the Golden Scale - Millholm Branch",
        attributes=[
            ("desc",
             "Polished marble floors reflect ornate chandeliers overhead. "
             "Massive stone columns support a vaulted ceiling adorned with "
             "golden scale motifs. Behind an elaborate wrought-iron barrier, "
             "clerks in fine robes work at mahogany desks with precise, "
             "practiced movements. Heavy vault doors of reinforced steel "
             "stand sentinel at the rear, guarded by stern-faced sentries "
             "in the Order's distinctive livery. A polished brass sign "
             "on the counter lists the services available."),
            ("details", {
                "vault": (
                    "Massive steel doors, each as thick as a man's arm, "
                    "covered in locking mechanisms of increasing complexity. "
                    "The Order's crest — a golden scale balanced on a sword "
                    "— is cast into the metal. The sentries standing before "
                    "it do not look like people who enjoy conversation."
                ),
                "vault doors": (
                    "Massive steel doors, each as thick as a man's arm, "
                    "covered in locking mechanisms of increasing complexity. "
                    "The Order's crest — a golden scale balanced on a sword "
                    "— is cast into the metal. The sentries standing before "
                    "it do not look like people who enjoy conversation."
                ),
                "sign": (
                    "A polished brass plaque reads:\n"
                    "  |wBANKING SERVICES|n\n"
                    "  |wbalance|n              — view your account\n"
                    "  |wdeposit|n |c<item>|n        — store an item or resource\n"
                    "  |wdeposit|n |c<amount> <item>|n — store a quantity\n"
                    "  |wwithdraw|n |c<item>|n       — retrieve an item or resource\n"
                    "  |wwithdraw|n |c<amount> <item>|n — retrieve a quantity"
                ),
            }),
        ],
    )

    # ── Master Oakwright's Woodshop (Crafting — woodshop) ────────────
    rooms["woodshop"] = create_object(
        RoomCrafting,
        key="Master Oakwright's Woodshop",
        attributes=[
            ("crafting_type", "woodshop"),
            ("mastery_level", 1),
            ("craft_cost", 2),
            ("desc",
             "The rich scent of freshly cut timber fills this workshop. "
             "Workbenches scarred from years of sawing and planing line the "
             "walls. Hand tools hang in neat rows — chisels, planes, saws, "
             "mallets of every size. Wood shavings curl across the floor "
             "like golden ribbons, and sawdust motes dance in the beams of "
             "light from high windows."),
        ],
    )

    # ── Millholm General Store ──────────────────────────────────────
    rooms["general_store"] = create_object(
        RoomBase,
        key="Millholm General Store",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Wooden shelves line every wall, stocked with everything from "
             "iron nails and rope to bolt cloth and pottery. Barrels of "
             "grain and preserved foods occupy the floor. Hanging from the "
             "ceiling are coils of rope, dried herbs, and farming tools. "
             "Behind the polished oak counter, countless small drawers "
             "contain needles, thread, buttons, and sundries."),
        ],
    )

    # ── Abandoned House (secondary sewer entrance) ───────────────────
    rooms["abandoned_house"] = create_object(
        RoomBase,
        key="Abandoned House",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "Dusty furniture sits beneath cobweb-draped sheets. The windows "
             "are boarded from inside. Despite the decay, the structure is "
             "surprisingly solid. A musty smell of disuse fills the air, "
             "though faint scratches and occasional creaks suggest the "
             "building may not be entirely unoccupied."),
        ],
    )

    # ── Retail shops on Old Trade Way ───────────────────────────────

    rooms["weapons_shop"] = create_object(
        RoomBase,
        key="Grik's Blades & Blunts",
        attributes=[
            ("desc",
             "Racks of weapons line every wall of this compact shop — "
             "wooden training swords beside iron blades, daggers displayed "
             "under glass, and heavier weapons mounted on brackets above. "
             "A battered sign reads 'Blades & Blunts — Buy, Sell, Trade.' "
             "The proprietor, a wiry goblin with a surprisingly keen "
             "business sense, perches behind a counter cluttered with "
             "whetstones and weapon oil."),
        ],
    )

    rooms["armorer"] = create_object(
        RoomBase,
        key="Ironclad Outfitters",
        attributes=[
            ("desc",
             "Mannequins stand in rows wearing suits of armour from "
             "simple leather jerkins to heavy iron hauberks. Shields of "
             "every size hang on the walls, their surfaces polished to "
             "a mirror sheen. A workbench near the back holds tools for "
             "last-minute adjustments — every piece is fitted to the "
             "buyer before it leaves the shop."),
        ],
    )

    rooms["clothing_shop"] = create_object(
        RoomBase,
        key="The Silken Thread",
        attributes=[
            ("desc",
             "Bolts of fabric in every colour fill the shelves of this "
             "elegant shop. Cloaks hang from iron hooks, boots are lined "
             "up in neat rows, and glass cases display delicate scarves, "
             "sashes, and enchanted accessories. The air smells of "
             "lavender and cedar — the proprietor takes pride in "
             "keeping moths at bay."),
        ],
    )

    rooms["magical_supplies"] = create_object(
        RoomBase,
        key="The Bubbling Flask",
        attributes=[
            ("desc",
             "Glass bottles of every shape and colour crowd the shelves "
             "of this dimly lit shop. Potions glow faintly in their "
             "stoppered vials — amber, emerald, deep violet. Bundles "
             "of dried herbs hang from the ceiling beams, and a faint "
             "haze of aromatic smoke drifts from an incense burner on "
             "the counter. A hand-lettered sign warns 'You Break It, "
             "You Bought It.'"),
        ],
    )

    rooms["jewellers_showroom"] = create_object(
        RoomBase,
        key="The Gilded Window",
        attributes=[
            ("desc",
             "Velvet-lined display cases hold rings, chains, bangles, "
             "and ear studs wrought in copper, pewter, and silver. "
             "Enchanted gems catch the lamplight and throw tiny "
             "rainbows across the walls. This is the retail front for "
             "The Gilded Setting workshop — finished pieces are brought "
             "here from Artisan's Way for sale to the public."),
        ],
    )

    rooms["vacant_shop"] = create_object(
        RoomBase,
        key="Vacant Shopfront",
        attributes=[
            ("desc",
             "An empty shop with bare shelves and a cold hearth. The "
             "windows are clean but the display cases are empty. A "
             "faded 'To Let — Inquire at Town Hall' notice is pinned "
             "inside the glass door. Whatever business occupied this "
             "prime Trade Way frontage has moved on."),
        ],
    )

    print(f"  Created {len(rooms)} rooms.")

    # ══════════════════════════════════════════════════════════════════
    # 2. CREATE EXITS
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # ── Limbo → Inn connection ───────────────────────────────────────
    if one_way_limbo:
        exit_ab = create_object(
            ExitVerticalAware,
            key=rooms["inn"].key,
            location=limbo,
            destination=rooms["inn"],
        )
        exit_ab.set_direction("down")
        exit_count += 1
    else:
        connect_bidirectional_exit(limbo, rooms["inn"], "down")
        exit_count += 2

    # ── Trade Way: west approach → square → east departure ───────────
    #
    #  road_far_west → road_mid_west → road_west → sq_w → sq_center → sq_e → road_east → road_mid_east → road_far_east
    #
    connect_bidirectional_exit(rooms["road_far_west"], rooms["road_mid_west"], "east")
    connect_bidirectional_exit(rooms["road_mid_west"], rooms["road_west"], "east")
    connect_bidirectional_exit(rooms["road_west"], rooms["sq_w"], "east")
    connect_bidirectional_exit(rooms["sq_w"], rooms["sq_center"], "east")
    connect_bidirectional_exit(rooms["sq_center"], rooms["sq_e"], "east")
    connect_bidirectional_exit(rooms["sq_e"], rooms["road_east"], "east")
    connect_bidirectional_exit(rooms["road_east"], rooms["road_mid_east"], "east")
    connect_bidirectional_exit(rooms["road_mid_east"], rooms["road_far_east"], "east")
    exit_count += 16

    # ── NS road through square ───────────────────────────────────────
    connect_bidirectional_exit(rooms["sq_n"], rooms["sq_center"], "south")
    connect_bidirectional_exit(rooms["sq_center"], rooms["sq_s"], "south")
    exit_count += 4

    # ── 3x3 square internal connections ──────────────────────────────
    # North row: nw ↔ n ↔ ne
    connect_bidirectional_exit(rooms["sq_nw"], rooms["sq_n"], "east")
    connect_bidirectional_exit(rooms["sq_n"], rooms["sq_ne"], "east")
    exit_count += 4

    # South row: sw ↔ s ↔ se
    connect_bidirectional_exit(rooms["sq_sw"], rooms["sq_s"], "east")
    connect_bidirectional_exit(rooms["sq_s"], rooms["sq_se"], "east")
    exit_count += 4

    # North-south between corner rows and middle row
    # West column: nw ↔ w ↔ sw
    connect_bidirectional_exit(rooms["sq_nw"], rooms["sq_w"], "south")
    connect_bidirectional_exit(rooms["sq_w"], rooms["sq_sw"], "south")
    exit_count += 4

    # East column: ne ↔ e ↔ se
    connect_bidirectional_exit(rooms["sq_ne"], rooms["sq_e"], "south")
    connect_bidirectional_exit(rooms["sq_e"], rooms["sq_se"], "south")
    exit_count += 4

    # ── North road ─────────────────────────────────────────────────
    connect_bidirectional_exit(rooms["sq_n"], rooms["north_road"], "north")
    exit_count += 2

    # ── South road (full spine to south gate) ─────────────────────────
    connect_bidirectional_exit(rooms["sq_s"], rooms["south_road"], "south")
    connect_bidirectional_exit(rooms["south_road"], rooms["mid_south_road"], "south")
    connect_bidirectional_exit(rooms["mid_south_road"], rooms["upper_south_road"], "south")
    connect_bidirectional_exit(rooms["upper_south_road"], rooms["artisans_way"], "south")
    connect_bidirectional_exit(rooms["artisans_way"], rooms["lower_south_road"], "south")
    connect_bidirectional_exit(rooms["lower_south_road"], rooms["far_south_road"], "south")
    connect_bidirectional_exit(rooms["far_south_road"], rooms["south_gate"], "south")
    exit_count += 14

    # Lower south road — west to jeweller (second entrance)
    connect_bidirectional_door_exit(
        rooms["lower_south_road"], rooms["jeweller"], "west",
        key="a wooden door",
        closed_ab="A wooden door with a gem-and-ring sign leads west.",
        open_ab="The glint of precious metals catches the light through the open door.",
        closed_ba="A wooden door leads east to South Road.",
        open_ba="South Road is visible through the open door.",
    )
    exit_count += 2

    # Upper south road — east to apothecary (second entrance)
    connect_bidirectional_door_exit(
        rooms["upper_south_road"], rooms["apothecary"], "east",
        key="a wooden door",
        closed_ab="A wooden door with a mortar and pestle sign leads east.",
        open_ab="The sharp scent of herbs drifts through the open door.",
        closed_ba="A wooden door leads west to South Road.",
        open_ba="South Road is visible through the open door.",
    )
    exit_count += 2

    # Artisan's Way — west branch
    connect_bidirectional_exit(rooms["artisans_way"], rooms["artisans_way_w1"], "west")
    connect_bidirectional_exit(rooms["artisans_way_w1"], rooms["artisans_way_w2"], "west")
    connect_bidirectional_exit(rooms["artisans_way_w2"], rooms["artisans_way_w3"], "west")
    exit_count += 6

    # Artisan's Way — east branch
    connect_bidirectional_exit(rooms["artisans_way"], rooms["artisans_way_e1"], "east")
    connect_bidirectional_exit(rooms["artisans_way_e1"], rooms["artisans_way_e2"], "east")
    connect_bidirectional_exit(rooms["artisans_way_e2"], rooms["artisans_way_e3"], "east")
    exit_count += 6

    # ── Artisan's Way — craft room doors (north and south off lane) ──

    # W3 north: Hendricks House — south: Leathershop
    connect_bidirectional_door_exit(
        rooms["artisans_way_w3"], rooms["hendricks_house"], "north",
        key="a wooden door",
        closed_ab="A wooden door leads north to a modest dwelling.",
        open_ab="A cosy room with a well-worn armchair is visible through the open door.",
        closed_ba="A wooden door leads south to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    connect_bidirectional_door_exit(
        rooms["artisans_way_w3"], rooms["leathershop"], "south",
        key="a wooden door",
        closed_ab="A wooden door with a leather hide sign leads south.",
        open_ab="The sharp smell of tanned leather drifts through the open door.",
        closed_ba="A wooden door leads north to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    exit_count += 4

    # W2 north: Smithy — south: Vacant
    connect_bidirectional_door_exit(
        rooms["artisans_way_w2"], rooms["smithy"], "north",
        key="a heavy iron door",
        closed_ab="A heavy iron door leads north into a smithy.",
        open_ab="Heat and the ring of hammer on anvil pour through the open door.",
        closed_ba="A heavy iron door leads south to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    connect_bidirectional_exit(rooms["artisans_way_w2"], rooms["vacant_w2"], "south",
            desc_ab="a boarded-up workshop", desc_ba="Artisan's Way")
    exit_count += 4

    # W1 north: Vacant (ground only) — south: Jeweller
    exit_to_vacant, _ = connect_bidirectional_exit(rooms["artisans_way_w1"], rooms["vacant_w1"], "north",
            desc_ab="a shuttered workshop", desc_ba="Artisan's Way")
    exit_to_vacant.required_min_height = 0
    exit_to_vacant.required_max_height = 0
    door_jeweller_ab, _ = connect_bidirectional_door_exit(
        rooms["artisans_way_w1"], rooms["jeweller"], "south",
        key="a wooden door",
        closed_ab="A wooden door with a gem-and-ring sign leads south.",
        open_ab="The glint of gems and precious metals catches the light through the open door.",
        closed_ba="A wooden door leads north to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    door_jeweller_ab.required_min_height = 0
    door_jeweller_ab.required_max_height = 0
    exit_count += 4

    # E1 north: Apothecary — south: Distillery (back room off apothecary)
    connect_bidirectional_door_exit(
        rooms["artisans_way_e1"], rooms["apothecary"], "north",
        key="a wooden door",
        closed_ab="A wooden door with a mortar and pestle sign leads north.",
        open_ab="Strange scents and coloured vapours drift through the open door.",
        closed_ba="A wooden door leads south to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    connect_bidirectional_exit(rooms["apothecary"], rooms["distillery"], "east",
            desc_ab="the distillery", desc_ba="the apothecary")
    exit_count += 4

    # E2 north: Textiles — south: Vacant
    connect_bidirectional_door_exit(
        rooms["artisans_way_e2"], rooms["textiles"], "north",
        key="a wooden door",
        closed_ab="A wooden door with colourful fabric samples in the window leads north.",
        open_ab="Bolts of colourful fabric are visible through the open door.",
        closed_ba="A wooden door leads south to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    connect_bidirectional_exit(rooms["artisans_way_e2"], rooms["vacant_e2"], "south",
            desc_ab="a disused workshop", desc_ba="Artisan's Way")
    exit_count += 4

    # E3 north: Elena Copperkettle's House — south: Woodshop
    connect_bidirectional_door_exit(
        rooms["artisans_way_e3"], rooms["elena_house"], "north",
        key="a wooden door",
        closed_ab="A wooden door leads north to a cosy cottage.",
        open_ab="The smell of tea and fabric fills the air through the open door.",
        closed_ba="A wooden door leads south to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    connect_bidirectional_door_exit(
        rooms["artisans_way_e3"], rooms["woodshop"], "south",
        key="a wooden door",
        closed_ab="A wooden door with a carved oak leaf sign leads south.",
        open_ab="The scent of fresh-cut wood wafts through the open door.",
        closed_ba="A wooden door leads north to Artisan's Way.",
        open_ba="Artisan's Way is visible through the open door.",
    )
    exit_count += 4

    # ── Buildings off the square (doors) ─────────────────────────────

    # NW — Inn (south door from inn to sq_nw)
    connect_bidirectional_door_exit(
        rooms["inn"], rooms["sq_nw"], "south",
        key="a wooden door",
        closed_ab="A wooden door leads south to the market square.",
        open_ab="The bustle of the market square is visible through the open door.",
        closed_ba="A sturdy wooden door leads north into The Harvest Moon inn.",
        open_ba="Warmth and the aroma of cooking food pour through the open door.",
    )
    exit_count += 2

    # NE — Stables (north door from sq_ne)
    connect_bidirectional_door_exit(
        rooms["sq_ne"], rooms["stables"], "north",
        key="large double doors",
        door_name="doors",
        closed_ab="Large double doors lead north into the town stables.",
        open_ab="The open stable doors reveal stalls of horses within.",
        closed_ba="Large double doors lead south to the market square.",
        open_ba="The market square is visible through the open doors.",
    )
    exit_count += 2

    # NE — Bakery (east door from sq_ne)
    connect_bidirectional_door_exit(
        rooms["sq_ne"], rooms["bakery"], "east",
        key="a wooden door",
        closed_ab="A wooden door leads east into Goldencrust Bakery.",
        open_ab="The heavenly aroma of fresh bread pours through the open door.",
        closed_ba="A wooden door leads west to the market square.",
        open_ba="The market square is visible through the open door.",
    )
    exit_count += 2

    # road_mid_west — Armorer (north door, replaces old smithy)
    connect_bidirectional_door_exit(
        rooms["road_mid_west"], rooms["armorer"], "north",
        key="a reinforced door",
        closed_ab="A reinforced door with crossed-swords insignia leads north.",
        open_ab="Rows of gleaming armour on mannequins are visible through the open door.",
        closed_ba="A reinforced door leads south to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_far_west — Abandoned House (south door)
    connect_bidirectional_door_exit(
        rooms["road_far_west"], rooms["abandoned_house"], "south",
        key="a boarded-up door",
        closed_ab="A boarded-up door leads south into a disused building.",
        open_ab="Dust and cobwebs are visible through the gap in the boards.",
        closed_ba="A boarded-up door leads north to the trade road.",
        open_ba="Daylight filters in from the trade road beyond.",
    )
    exit_count += 2

    # SW — Shrine (south door)
    connect_bidirectional_door_exit(
        rooms["sq_sw"], rooms["shrine"], "south",
        key="ornate double doors",
        door_name="doors",
        closed_ab="Ornate double doors carved with harvest motifs lead south.",
        open_ab="Candlelight and the scent of incense drift through the open doors.",
        closed_ba="Ornate double doors lead north to the market square.",
        open_ba="The sounds of the market square drift in through the open doors.",
    )
    exit_count += 2

    # SW — General Store (west door)
    connect_bidirectional_door_exit(
        rooms["sq_sw"], rooms["general_store"], "west",
        key="a wooden door",
        closed_ab="A wooden door with a painted 'General Store' sign leads west.",
        open_ab="Shelves laden with goods are visible through the open door.",
        closed_ba="A wooden door leads east to the market square.",
        open_ba="The market square is visible through the open door.",
    )
    exit_count += 2

    # road_west — General Store (south door, 2nd entrance)
    connect_bidirectional_door_exit(
        rooms["road_west"], rooms["general_store"], "south",
        key="a wooden door",
        closed_ab="A wooden door with a painted 'General Store' sign leads south.",
        open_ab="Shelves laden with goods are visible through the open door.",
        closed_ba="A wooden door leads north to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # SE — Mages Guild (south door)
    connect_bidirectional_door_exit(
        rooms["sq_se"], rooms["mages_guild"], "south",
        key="a plain wooden door",
        closed_ab="A plain wooden door leads south into a modest building.",
        open_ab="Arcane symbols and flickering lights are visible through the open door.",
        closed_ba="A plain wooden door leads north to the market square.",
        open_ba="Daylight and market sounds pour through the open door.",
    )
    exit_count += 2

    # sq_se — Bank (east door, 2nd entrance)
    connect_bidirectional_door_exit(
        rooms["sq_se"], rooms["bank"], "east",
        key="a grand bronze door",
        closed_ab=(
            "A grand bronze door bearing the crest of the Order of the "
            "Golden Scale leads east."
        ),
        open_ab="Marble floors and ornate chandeliers are visible through the open door.",
        closed_ba="A grand bronze door leads west to the market square.",
        open_ba="The market square is visible through the open door.",
    )
    exit_count += 2

    # ── Buildings off the approach roads (doors) ─────────────────────

    # road_far_west — Weapons Shop (north door, replaces old textiles)
    connect_bidirectional_door_exit(
        rooms["road_far_west"], rooms["weapons_shop"], "north",
        key="a wooden door",
        closed_ab="A wooden door beneath a sign reading 'Blades & Blunts' leads north.",
        open_ab="Racks of weapons gleam in the lamplight through the open door.",
        closed_ba="A wooden door leads south to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_west — Clothing Shop (north door, replaces old woodshop)
    connect_bidirectional_door_exit(
        rooms["road_west"], rooms["clothing_shop"], "north",
        key="a wooden door",
        closed_ab="A wooden door with elegant fabric drapes in the window leads north.",
        open_ab="Displays of cloaks, boots, and fine accessories are visible through the open door.",
        closed_ba="A wooden door leads south to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_mid_west — Gareth Stonefield's House (south door)
    connect_bidirectional_door_exit(
        rooms["road_mid_west"], rooms["gareth_house"], "south",
        key="an impressive oak door",
        closed_ab=(
            "An impressive oak door with brass fittings leads south to a "
            "fine merchant residence."
        ),
        open_ab="Quality furnishings and maps are visible through the open door.",
        closed_ba="An impressive oak door leads north to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # sq_nw — Clothing Shop (west door, 2nd entrance)
    connect_bidirectional_door_exit(
        rooms["sq_nw"], rooms["clothing_shop"], "west",
        key="a wooden door",
        closed_ab="A wooden door leads west into The Silken Thread.",
        open_ab="Bolts of colourful fabric are visible through the open door.",
        closed_ba="A wooden door leads east to the market square.",
        open_ba="The market square is visible through the open door.",
    )
    exit_count += 2

    # road_east — Bakery (north door, 2nd entrance)
    connect_bidirectional_door_exit(
        rooms["road_east"], rooms["bakery"], "north",
        key="a wooden door",
        closed_ab="A wooden door leads north into Goldencrust Bakery.",
        open_ab="The heavenly aroma of fresh bread pours through the open door.",
        closed_ba="A wooden door leads south to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_east — Bank (south door)
    connect_bidirectional_door_exit(
        rooms["road_east"], rooms["bank"], "south",
        key="a grand bronze door",
        closed_ab=(
            "A grand bronze door bearing the crest of the Order of the "
            "Golden Scale leads south."
        ),
        open_ab="Marble floors and ornate chandeliers are visible through the open door.",
        closed_ba="A grand bronze door leads north to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_mid_east — Magical Supplies (north door, replaces old apothecary)
    connect_bidirectional_door_exit(
        rooms["road_mid_east"], rooms["magical_supplies"], "north",
        key="a wooden door",
        closed_ab="A wooden door with a bubbling flask sign leads north.",
        open_ab="The glow of coloured potions is visible through the open door.",
        closed_ba="A wooden door leads south to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_mid_east — Post Office (south door)
    connect_bidirectional_door_exit(
        rooms["road_mid_east"], rooms["post_office"], "south",
        key="a sturdy oak door",
        closed_ab="A sturdy oak door with a brass letterbox leads south.",
        open_ab="A tidy counter and wall of pigeon-holes are visible through the open door.",
        closed_ba="A sturdy oak door leads north to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_far_east — Jeweller's Showroom (north door, replaces old jeweller)
    connect_bidirectional_door_exit(
        rooms["road_far_east"], rooms["jewellers_showroom"], "north",
        key="a wooden door",
        closed_ab="A wooden door with a gilded window display leads north.",
        open_ab="Enchanted gems sparkle in velvet-lined cases through the open door.",
        closed_ba="A wooden door leads south to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # road_far_east — Vacant Shopfront (south door, replaces old leathershop)
    connect_bidirectional_door_exit(
        rooms["road_far_east"], rooms["vacant_shop"], "south",
        key="a glass door",
        closed_ab="A glass-panelled door with a 'To Let' notice leads south.",
        open_ab="An empty shop with bare shelves is visible through the open door.",
        closed_ba="A glass-panelled door leads north to the trade road.",
        open_ba="The trade road is visible through the open door.",
    )
    exit_count += 2

    # ── Buildings off South Road (doors) ───────────────────────────

    # south_road — Temple (west door, 2nd entrance)
    connect_bidirectional_door_exit(
        rooms["south_road"], rooms["shrine"], "west",
        key="ornate double doors",
        door_name="doors",
        closed_ab="Ornate double doors carved with harvest motifs lead west.",
        open_ab="Candlelight and the scent of incense drift through the open doors.",
        closed_ba="Ornate double doors lead east to the south road.",
        open_ba="The south road is visible through the open doors.",
    )
    exit_count += 2

    # mid_south_road — Warriors Guild (east door)
    connect_bidirectional_door_exit(
        rooms["mid_south_road"], rooms["warriors_guild"], "east",
        key="a sturdy wooden door",
        closed_ab="A sturdy door marked with The Iron Company coat of arms leads east.",
        open_ab="The clang of practice weapons echoes through the open door.",
        closed_ba="A sturdy wooden door leads west to the south road.",
        open_ba="The south road is visible through the open door.",
    )
    exit_count += 2

    # mid_south_road — Beggar's Alley (west)
    connect_bidirectional_exit(rooms["mid_south_road"], rooms["beggars_alley"], "west")
    exit_count += 2

    # far_south_road — Broken Crown (west door)
    connect_bidirectional_door_exit(
        rooms["far_south_road"], rooms["broken_crown"], "west",
        key="a battered wooden door",
        closed_ab="A battered wooden door beneath a cracked crown sign leads west.",
        open_ab="The smell of stale ale and pipe smoke drifts through the open door.",
        closed_ba="A battered wooden door leads east to the south road.",
        open_ba="The south road is visible through the open door.",
    )
    exit_count += 2

    # far_south_road — Gaol (east door)
    connect_bidirectional_door_exit(
        rooms["far_south_road"], rooms["gaol"], "east",
        key="a heavy iron-banded door",
        closed_ab="A heavy iron-banded door leads east into the town gaol.",
        open_ab="The damp, cold air of the gaol seeps through the open door.",
        closed_ba="A heavy iron-banded door leads west to the south road.",
        open_ba="The south road is visible through the open door.",
    )

    # Gaol — Cell (locked door north)
    connect_bidirectional_door_exit(
        rooms["gaol"], rooms["gaol_cell"], "north",
        key="a barred cell door",
        closed_ab="A barred iron cell door leads north. It is locked.",
        open_ab="The cell door stands open, revealing a cramped stone cell.",
        closed_ba="A barred iron cell door blocks the way south to the gaol.",
        open_ba="The guard's desk and the gaol corridor are visible through the open door.",
        door_name="cell door",
        is_locked=True,
        lock_dc=12,
    )
    exit_count += 2
    exit_count += 2

    # ── Gareth's House → Bedroom (upstairs) ─────────────────────────
    connect_bidirectional_exit(rooms["gareth_house"], rooms["gareth_bedroom"], "up",
            desc_ab="the bedroom upstairs", desc_ba="the house below")
    exit_count += 2

    # ── Secret passage: Gareth's House ↔ Abandoned House (hidden) ────
    secret_ab, secret_ba = connect_bidirectional_exit(
        rooms["gareth_house"], rooms["abandoned_house"], "west",
        desc_ab=(
            "The west wall is decorated with an impressive bookcase housing "
            "a large collection of leather-bound tomes on trade, economics, "
            "and geography."
        ),
        desc_ba=(
            "Footprints in the thick dust lead across the room toward the "
            "east wall and simply stop, as if whoever made them vanished "
            "into thin air."
        ),
    )
    secret_ab.is_hidden = True
    secret_ab.find_dc = 12
    secret_ba.is_hidden = True
    secret_ba.find_dc = 12
    exit_count += 2

    # ── NPC house connections behind shops ───────────────────────────
    # Hendricks House — now accessed from Artisan's Way W3 (north door above)
    # Elena's House — now accessed from Artisan's Way E3 (north door above)

    # Mara Brightwater — behind (north of) apothecary (stays as internal connection)
    connect_bidirectional_exit(rooms["apothecary"], rooms["mara_house"], "north",
            desc_ab="a door to a cottage",
            desc_ba="the apothecary workshop")
    exit_count += 2

    # ── Inn vertical chain ───────────────────────────────────────────
    connect_bidirectional_exit(rooms["inn"], rooms["stairwell"], "north",
            desc_ab="a narrow stairwell", desc_ba="The Harvest Moon")
    connect_bidirectional_exit(rooms["stairwell"], rooms["cellar_stairwell"], "down",
            desc_ab="stairs descending into the cellar",
            desc_ba="stairs leading back up")
    connect_bidirectional_exit(rooms["stairwell"], rooms["first_floor_stairwell"], "up",
            desc_ab="stairs leading to the first floor",
            desc_ba="stairs leading back down")
    # NOTE: cellar_stairwell → cellar connection is now a door (soft_deploy.py)
    # created in build_game_world.py (rat cellar quest). Return exit from cellar
    # back to cellar_stairwell is also wired there.
    connect_bidirectional_exit(rooms["first_floor_stairwell"], rooms["hallway"], "south",
            desc_ab="the upstairs hallway",
            desc_ba="the first floor stairwell")
    connect_bidirectional_exit(rooms["hallway"], rooms["bedroom_east"], "east",
            desc_ab="a bedroom", desc_ba="the hallway")
    connect_bidirectional_exit(rooms["hallway"], rooms["bedroom_west"], "west",
            desc_ab="a bedroom", desc_ba="the hallway")
    exit_count += 12  # was 14, minus 2 for cellar door (moved to build_game_world)

    # ── Guild back rooms ─────────────────────────────────────────────
    connect_bidirectional_exit(rooms["shrine"], rooms["priest_quarters"], "up",
            desc_ab="the priest's quarters", desc_ba="the shrine")
    connect_bidirectional_exit(rooms["mages_guild"], rooms["arcane_study"], "east",
            desc_ab="an arcane study", desc_ba="the guild hall")
    connect_bidirectional_exit(rooms["warriors_guild"], rooms["barracks"], "south",
            desc_ab="the barracks", desc_ba="the guild hall")
    exit_count += 6

    print(f"  Created {exit_count} exits.")

    # ══════════════════════════════════════════════════════════════════
    # 3. TAG ROOMS — zone, district, terrain
    # ══════════════════════════════════════════════════════════════════

    all_rooms = list(rooms.values())
    for room in all_rooms:
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # Terrain types — outdoor urban
    outdoor_urban = [
        rooms["sq_nw"], rooms["sq_n"], rooms["sq_ne"],
        rooms["sq_w"], rooms["sq_center"], rooms["sq_e"],
        rooms["sq_sw"], rooms["sq_s"], rooms["sq_se"],
        rooms["road_west"], rooms["road_east"],
        rooms["road_mid_west"], rooms["road_mid_east"],
        rooms["stables"], rooms["north_road"],
        rooms["south_road"], rooms["mid_south_road"],
        rooms["upper_south_road"], rooms["lower_south_road"],
        rooms["far_south_road"], rooms["south_gate"],
        rooms["artisans_way"],
        rooms["artisans_way_w1"], rooms["artisans_way_w2"],
        rooms["artisans_way_w3"],
        rooms["artisans_way_e1"], rooms["artisans_way_e2"],
        rooms["artisans_way_e3"],
    ]
    for room in outdoor_urban:
        room.set_terrain(TerrainType.URBAN.value)

    # Road endpoints transition to rural
    rooms["road_far_west"].set_terrain(TerrainType.RURAL.value)
    rooms["road_far_east"].set_terrain(TerrainType.RURAL.value)

    # Cemetery area — rural

    # Indoor rooms — urban terrain (inside town buildings)
    indoor_rooms = [
        r for r in all_rooms
        if r not in outdoor_urban
        and r is not rooms["road_far_west"]
        and r is not rooms["road_far_east"]
    ]
    for room in indoor_rooms:
        room.set_terrain(TerrainType.URBAN.value)

    # Cellar, back cellar, and stairwell are underground but torchlit
    rooms["cellar"].set_terrain(TerrainType.UNDERGROUND.value)
    rooms["cellar"].always_lit = True
    rooms["back_cellar"].set_terrain(TerrainType.UNDERGROUND.value)
    rooms["back_cellar"].always_lit = True
    rooms["cellar_stairwell"].set_terrain(TerrainType.UNDERGROUND.value)
    rooms["cellar_stairwell"].always_lit = True

    print("  Tagged all rooms with zone, district, and terrain.")

    # ── Street flying height ─────────────────────────────────────────
    # All outdoor streets allow flight up to height 2 so flying
    # characters see a consistent sky layer across town. Rooftop
    # access via height-routed exits only exists on specific streets.
    flyable_streets = [
        # Old Trade Way
        rooms["road_far_west"], rooms["road_west"],
        rooms["road_mid_west"], rooms["road_mid_east"],
        rooms["road_east"], rooms["road_far_east"],
        # Market Square (all 9 cells)
        rooms["sq_nw"], rooms["sq_n"], rooms["sq_ne"],
        rooms["sq_w"], rooms["sq_center"], rooms["sq_e"],
        rooms["sq_sw"], rooms["sq_s"], rooms["sq_se"],
        # North road
        rooms["north_road"],
        # South roads
        rooms["south_road"], rooms["mid_south_road"],
        rooms["upper_south_road"], rooms["lower_south_road"],
        rooms["far_south_road"], rooms["south_gate"],
        # Artisan's Way (w1 already set in room creation)
        rooms["artisans_way"],
        rooms["artisans_way_e1"], rooms["artisans_way_e2"],
        rooms["artisans_way_e3"],
    ]
    for room in flyable_streets:
        room.max_height = 2
    print(f"  Set max_height=2 on {len(flyable_streets) + 1} flyable streets.")

    # ── Indoor flying restriction ────────────────────────────────────
    # Indoor rooms should not allow any flying (max_height=0).
    # Rooms already set via create_object attributes are excluded.
    no_fly_interiors = [
        rooms["inn"], rooms["bakery"], rooms["smithy"],
        rooms["leathershop"], rooms["textiles"], rooms["jeweller"],
        rooms["apothecary"], rooms["woodshop"], rooms["bank"],
        rooms["post_office"], rooms["broken_crown"], rooms["gaol"],
        rooms["gaol_cell"],
        rooms["weapons_shop"], rooms["armorer"], rooms["clothing_shop"],
        rooms["magical_supplies"], rooms["jewellers_showroom"],
        rooms["vacant_shop"], rooms["vacant_w1"],
        rooms["vacant_w2"], rooms["vacant_e2"],
    ]
    for room in no_fly_interiors:
        room.max_height = 0
    print(f"  Set max_height=0 on {len(no_fly_interiors)} indoor rooms.")

    # ── Combat flags ─────────────────────────────────────────────────
    # RoomBase defaults: allow_combat=True, allow_pvp=False, allow_death=True.
    # All no-combat rooms in Millholm Town.
    # Rooms using specialised typeclasses already have allow_combat=False
    # via their class definition — listed here as comments for reference:
    #   RoomInn:        inn
    #   RoomBank:       bank
    #   RoomPostOffice: post_office
    #   RoomCrafting:   smithy, leathershop, textiles, woodshop,
    #                   apothecary, jeweller, arcane_study
    #   RoomProcessing: distillery, bakery
    # Below: RoomBase rooms that need allow_combat set explicitly.
    no_combat_rooms = [
        rooms["mages_guild"],       # Circle of the First Light
        rooms["warriors_guild"],    # The Iron Company
        rooms["barracks"],          # attached to warriors guild
        rooms["shrine"],            # Shrine of the First Harvest
        rooms["priest_quarters"],   # attached to shrine
        rooms["stables"],           # Millholm Stables
        rooms["beggars_alley"],     # quest NPC Old Silas lives here
        rooms["general_store"],     # shop
        rooms["vacant_w1"],         # empty workshop
        rooms["vacant_w2"],         # empty workshop
        rooms["vacant_e2"],         # empty workshop
        rooms["weapons_shop"],      # retail shop
        rooms["armorer"],           # retail shop
        rooms["clothing_shop"],     # retail shop
        rooms["magical_supplies"],  # retail shop
        rooms["jewellers_showroom"],# retail shop
        rooms["vacant_shop"],       # empty shopfront
    ]
    for room in no_combat_rooms:
        room.allow_combat = False
    print("  Disabled combat in all town safe zones.")

    # ── Permanent lighting ────────────────────────────────────────────
    # Town streets have iron lampposts; inn has chandelier + oil lamps.
    # These rooms are never dark regardless of time of day.
    lit_streets = [
        rooms["sq_nw"], rooms["sq_n"], rooms["sq_ne"],
        rooms["sq_w"], rooms["sq_center"], rooms["sq_e"],
        rooms["sq_sw"], rooms["sq_s"], rooms["sq_se"],
        rooms["road_west"], rooms["road_east"],
        rooms["road_far_west"], rooms["road_far_east"],
        rooms["road_mid_west"], rooms["road_mid_east"],
        rooms["south_road"], rooms["mid_south_road"],
        rooms["upper_south_road"], rooms["lower_south_road"],
        rooms["far_south_road"], rooms["south_gate"],
        rooms["north_road"],
        rooms["artisans_way"],
        rooms["artisans_way_w1"], rooms["artisans_way_w2"],
        rooms["artisans_way_w3"],
        rooms["artisans_way_e1"], rooms["artisans_way_e2"],
        rooms["artisans_way_e3"],
    ]
    lamppost_detail = (
        "A tall iron lamppost topped with a glass-panelled lantern. "
        "The wick burns steadily behind the panes, kept lit by the "
        "town lamplighter each evening."
    )
    for room in lit_streets:
        room.always_lit = True
        details = dict(room.details) if room.details else {}
        details["lamppost"] = lamppost_detail
        details["lamp"] = lamppost_detail
        details["lantern"] = lamppost_detail
        room.details = details

    # Indoor rooms — workshops, shops, guilds, etc.
    # Lit by hearths, candles, oil lamps, or braziers.
    lit_interiors = [
        rooms["woodshop"], rooms["smithy"], rooms["apothecary"],
        rooms["textiles"], rooms["leathershop"], rooms["bank"],
        rooms["general_store"], rooms["mages_guild"],
        rooms["warriors_guild"], rooms["gaol"], rooms["gaol_cell"],
        rooms["broken_crown"], rooms["distillery"],
        rooms["post_office"],
        rooms["jeweller"], rooms["shrine"],
        rooms["priest_quarters"],
        rooms["vacant_w1"], rooms["vacant_w2"], rooms["vacant_e2"],
        rooms["weapons_shop"], rooms["armorer"],
        rooms["clothing_shop"], rooms["magical_supplies"],
        rooms["jewellers_showroom"], rooms["vacant_shop"],
        rooms["gareth_bedroom"],
    ]
    for room in lit_interiors:
        room.always_lit = True

    # Inn interior — already has always_lit via attributes.
    # Light the stairwells, hallway, and bedrooms too.
    inn_interior = [
        rooms["stairwell"], rooms["first_floor_stairwell"],
        rooms["hallway"], rooms["bedroom_east"], rooms["bedroom_west"],
    ]
    for room in inn_interior:
        room.always_lit = True

    print("  Set permanent lighting on town streets, shops, and inn.")

    # ── Weather exposure — outdoor rooms feel the weather ────────────
    # URBAN terrain defaults to sheltered (muffled indoor sounds).
    # Streets, square, and open alleys are exposed to the sky.
    outdoor_exposed = lit_streets + [
        rooms["beggars_alley"],
    ]
    for room in outdoor_exposed:
        room.sheltered = False

    print("  Set sheltered=False on outdoor streets and alleys.")

    # ══════════════════════════════════════════════════════════════════
    # 4. FUTURE CONNECTION NOTES
    # ══════════════════════════════════════════════════════════════════
    # road_far_west → will connect west to Millholm Farms district
    # road_far_east → will connect east to Industries / Millholm Woods
    # cellar → connects west (hidden) to Millholm Sewers (soft_deploy.py)
    # cellar → connects south via ConditionalDungeonExit (rat cellar quest)
    # abandoned_house → will connect down (hidden) to Millholm Sewers
    # south_gate → connects south to Southern District (build_game_world.py)

    # ── District map cell tags ────────────────────────────────────────
    # Tag convention: room.tags.add("<map_key>:<point_key>", category="map_cell")
    # millholm_town map — all exterior/street rooms
    _town_map_tags = {
        # ── Row 0-2: North road ──
        "north_road":          "millholm_town:north_road",
        # ── Row 3: above square ──
        "inn":                 "millholm_town:inn",
        "stables":             "millholm_town:stables",
        # ── Row 4: north shops + square top ──
        "weapons_shop":        "millholm_town:weapons_shop",
        "armorer":             "millholm_town:armorer",
        "clothing_shop":       "millholm_town:clothing_shop",
        "bakery":              "millholm_town:bakery",
        "magical_supplies":    "millholm_town:magical_supplies",
        "jewellers_showroom":  "millholm_town:jewellers_showroom",
        # ── Row 5: The Old Trade Way + Market Square ──
        "road_far_west":       "millholm_town:road_far_west",
        "road_west":           "millholm_town:road_west",
        "road_mid_west":       "millholm_town:road_mid_west",
        "sq_w":                "millholm_town:sq_w",
        "sq_nw":               "millholm_town:sq_nw",
        "sq_n":                "millholm_town:sq_n",
        "sq_ne":               "millholm_town:sq_ne",
        "sq_center":           "millholm_town:sq_center",
        "sq_sw":               "millholm_town:sq_sw",
        "sq_s":                "millholm_town:sq_s",
        "sq_se":               "millholm_town:sq_se",
        "sq_e":                "millholm_town:sq_e",
        "road_east":           "millholm_town:road_east",
        "road_mid_east":       "millholm_town:road_mid_east",
        "road_far_east":       "millholm_town:road_far_east",
        # ── Row 6: south side of Trade Way ──
        "gareth_house":        "millholm_town:gareth_house",
        "abandoned_house":     "millholm_town:abandoned_house",
        "general_store":       "millholm_town:general_store",
        "bank":                "millholm_town:bank",
        "post_office":         "millholm_town:post_office",
        "vacant_shop":         "millholm_town:vacant_shop",
        # ── Rows 7-8: south road (upper) ──
        "shrine":              "millholm_town:shrine",
        "south_road":          "millholm_town:south_road",
        "mages_guild":         "millholm_town:mages_guild",
        "beggars_alley":       "millholm_town:beggars_alley",
        "mid_south_road":      "millholm_town:mid_south_road",
        "warriors_guild":      "millholm_town:warriors_guild",
        # ── Row 9: north side of Artisan's Way ──
        "hendricks_house":     "millholm_town:hendricks_house",
        "smithy":              "millholm_town:smithy",
        "vacant_w1":           "millholm_town:vacant_w1",
        "upper_south_road":    "millholm_town:upper_south_road",
        "apothecary":          "millholm_town:apothecary",
        "textiles":            "millholm_town:textiles",
        "elena_house":         "millholm_town:elena_house",
        # ── Row 10: Artisan's Way lane ──
        "artisans_way_w3":     "millholm_town:artisans_way_w3",
        "artisans_way_w2":     "millholm_town:artisans_way_w2",
        "artisans_way_w1":     "millholm_town:artisans_way_w1",
        "artisans_way":        "millholm_town:artisans_way",
        "artisans_way_e1":     "millholm_town:artisans_way_e1",
        "artisans_way_e2":     "millholm_town:artisans_way_e2",
        "artisans_way_e3":     "millholm_town:artisans_way_e3",
        # ── Row 11: south side of Artisan's Way ──
        "leathershop":         "millholm_town:leathershop",
        "vacant_w2":           "millholm_town:vacant_w2",
        "jeweller":            "millholm_town:jeweller",
        "lower_south_road":    "millholm_town:lower_south_road",
        "gaol":                "millholm_town:gaol",
        "vacant_e2":           "millholm_town:vacant_e2",
        "woodshop":            "millholm_town:woodshop",
        # ── Row 12-13: far south road ──
        "broken_crown":        "millholm_town:broken_crown",
        "far_south_road":      "millholm_town:far_south_road",
        "gaol_cell":           "millholm_town:gaol_cell",
        "south_gate":          "millholm_town:south_gate",
    }
    for room_key, tag in _town_map_tags.items():
        rooms[room_key].tags.add(tag, category="map_cell")
    # ── Region map cell tags (3x3 town block) ──
    _rt = "millholm_region"
    # Top row: town_nw, town_n, town_ne
    for key in ["sq_nw", "inn", "weapons_shop", "clothing_shop"]:
        rooms[key].tags.add(f"{_rt}:town_nw", category="map_cell")
    for key in ["sq_n", "north_road"]:
        rooms[key].tags.add(f"{_rt}:town_n", category="map_cell")
    for key in ["sq_ne", "stables", "bakery",
                "magical_supplies", "jewellers_showroom"]:
        rooms[key].tags.add(f"{_rt}:town_ne", category="map_cell")
    # Middle row: town_w, town_center, town_e
    for key in ["road_far_west", "road_west", "road_mid_west", "sq_w",
                "abandoned_house", "general_store", "armorer"]:
        rooms[key].tags.add(f"{_rt}:town_w", category="map_cell")
    for key in ["sq_center", "sq_sw", "sq_s", "sq_se",
                "south_road", "shrine"]:
        rooms[key].tags.add(f"{_rt}:town_center", category="map_cell")
    for key in ["sq_e", "road_east", "road_mid_east", "road_far_east",
                "bank", "post_office", "vacant_shop"]:
        rooms[key].tags.add(f"{_rt}:town_e", category="map_cell")
    # Bottom row: town_sw, town_s (includes Artisan's Way), town_se
    for key in ["beggars_alley", "broken_crown",
                "artisans_way_w1", "artisans_way_w2", "artisans_way_w3",
                "smithy", "leathershop", "jeweller", "woodshop",
                "elena_house"]:
        rooms[key].tags.add(f"{_rt}:town_sw", category="map_cell")
    for key in ["mid_south_road", "upper_south_road", "lower_south_road",
                "far_south_road", "south_gate", "artisans_way"]:
        rooms[key].tags.add(f"{_rt}:town_s", category="map_cell")
    for key in ["warriors_guild", "mages_guild", "gaol",
                "artisans_way_e1", "artisans_way_e2", "artisans_way_e3",
                "apothecary", "textiles", "hendricks_house"]:
        rooms[key].tags.add(f"{_rt}:town_se", category="map_cell")
    print(f"  Tagged {len(_town_map_tags)} town rooms with map_cell tags (district + region).")

    print("  Millholm Town complete.\n")
    return rooms

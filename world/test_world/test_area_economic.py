
from evennia import create_object
from evennia import ObjectDB

# Import your typeclasses
from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_bank import RoomBank
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from typeclasses.terrain.rooms.room_inn import RoomInn
from typeclasses.terrain.rooms.room_cemetery import RoomCemetery
from typeclasses.terrain.rooms.room_processing import RoomProcessing
from typeclasses.terrain.exits.exit_trap_door import TrapDoor
from typeclasses.terrain.exits.exit_tripwire import TripwireExit
from typeclasses.terrain.rooms.room_pressure_plate import PressurePlateRoom
from typeclasses.world_objects.sign import WorldSign
from typeclasses.world_objects.trap_chest import TrapChest
from utils.exit_helpers import connect, connect_door


def test_area_economic():
    """
    Builds a simple test world
    """

    limbo = ObjectDB.objects.get(id=2)

    ##########################
    # dirt track - east west road connecting everything in the economic test area
    ##########################

    dt1 = create_object(
        RoomBase,
        key="dirt track 1",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this east west dirt track connects all the  economic test rooms")
        ]
    )

    # Sign in dirt track 1
    sign = create_object(WorldSign, key="a weathered sign", location=dt1)
    sign.sign_text = "Welcome to the Market District"
    sign.sign_style = "post"

    connect(limbo, dt1, "east", desc_ab="a small dirt track")

    dt2 = create_object(
        RoomBase,
        key="dirt track 2",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this east west dirt track connects all the  economic test rooms")
        ]
    )

    connect(dt1, dt2, "east", desc_ab="a small dirt track", desc_ba="a small dirt track")

    dt3 = create_object(
        RoomBase,
        key="dirt track 3",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this east west dirt track connects all the  economic test rooms")
        ]
    )

    connect(dt2, dt3, "east", desc_ab="a small dirt track", desc_ba="a small dirt track")

    dt3.always_lit = True
    dt3.details = {
        "lamp post": "A tall wrought-iron lamp post stands at the side of the track. "
                     "Its glass lantern glows with a steady, warm light that never "
                     "seems to flicker or fade.",
        "lamp": "A tall wrought-iron lamp post stands at the side of the track. "
                "Its glass lantern glows with a steady, warm light that never "
                "seems to flicker or fade.",
        "lantern": "A tall wrought-iron lamp post stands at the side of the track. "
                   "Its glass lantern glows with a steady, warm light that never "
                   "seems to flicker or fade.",
    }

    dt4 = create_object(
        RoomBase,
        key="dirt track 4",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this east west dirt track connects all the  economic test rooms")
        ]
    )

    connect(dt3, dt4, "east", desc_ab="a small dirt track", desc_ba="a small dirt track")

    dt5 = create_object(
        RoomBase,
        key="dirt track 5",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this east west dirt track connects all the  economic test rooms")
        ]
    )

    connect(dt4, dt5, "east", desc_ab="a small dirt track", desc_ba="a small dirt track")

    # --- Signs in dt5 ---
    # Hidden sign — requires 'search' to discover
    hidden_sign = create_object(WorldSign, key="faded signpost", location=dt5, nohome=True)
    hidden_sign.sign_text = "Beware: wolves ahead!"
    hidden_sign.sign_style = "post"
    hidden_sign.is_hidden = True
    hidden_sign.find_dc = 12

    # Invisible sign — requires DETECT_INVIS to see
    invis_sign = create_object(WorldSign, key="shimmering rune marker", location=dt5, nohome=True)
    invis_sign.sign_text = "The arcane wards hold strong."
    invis_sign.sign_style = "stone"
    invis_sign.is_invisible = True


    ##########################
    # wheat area
    ##########################

    wheat_farm = create_object(
        RoomHarvesting,
        key="Wheat Farm",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("resource_id", 1),
            ("harvest_height", 0),
            ("resource_count", 20),
            ("abundance_threshold", 5),
            ("harvest_command", "harvest"),
            ("desc_abundant", "Golden fields of wheat stretch out before you, swaying gently in the breeze. The crop is plentiful for 'harvest'."),
            ("desc_scarce", "The wheat field has been mostly harvested. A few stalks remain scattered about for 'harvest'."),
            ("desc_depleted", "The field is bare — every stalk of wheat has been harvested. It will need time to regrow."),
        ]
    )

    connect(dt1, wheat_farm, "south", desc_ab="a big field of wheat", desc_ba="a small dirt track")

    windmill = create_object(
        RoomProcessing,
        key="windmill",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("processing_type", "windmill"),
            ("process_cost", 1),
            ("recipes", [{"inputs": {1: 1}, "output": 2, "amount": 1, "cost": 1}]),
            ("desc", "A small, but functional windmill, where you can 'mill' your wheat to flour")
        ]
    )

    connect(wheat_farm, windmill, "south", desc_ab="a small windmill turns in the breeze", desc_ba="a big field of wheat")

    bakery = create_object(
        RoomProcessing,
        key="Artisanal Bakehouse",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("processing_type", "bakery"),
            ("process_cost", 1),
            ("recipes", [{"inputs": {2: 1, 6: 1}, "output": 3, "amount": 1, "cost": 1}]),
            ("desc", "this fancy pants, trendy and very expensive bakery has a window filled with delicious looking pastries. You can 'bake' flour and wood into bread here.")
        ]
    )

    connect_door(windmill, bakery, "south",
                 key="a heavy door",
                 closed_ab="a heavy door blocks the way",
                 open_ab="through an open door you see a busy, trendy looking Artisanal Bakehouse",
                 closed_ba="a heavy door blocks the way",
                 open_ba="through an open door you see a small windmill")


    ##########################
    # wood area
    ##########################

    forest = create_object(
        RoomHarvesting,
        key="Forest",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("resource_id", 6),
            ("resource_count", 20),
            ("harvest_height", 0),
            ("abundance_threshold", 5),
            ("harvest_command", "chop"),
            ("desc_abundant", "Tall oaks and sturdy pines crowd together in this dense woodland. Plenty of good timber to be had for those willing 'chop' it."),
            ("desc_scarce", "Stumps dot the clearing where trees once stood. A few suitable trunks await a good 'chop'."),
            ("desc_depleted", "The forest has been cleared — nothing but stumps and sawdust remain. It will take time for new growth."),
        ]
    )

    connect(dt2, forest, "south", desc_ab="a heavily wooded forest", desc_ba="a small dirt track")

    sawmill = create_object(
        RoomProcessing,
        key="sawmill",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("processing_type", "sawmill"),
            ("process_cost", 1),
            ("recipes", [{"inputs": {6: 1}, "output": 7, "amount": 1, "cost": 1}]),
            ("desc", "A sawmill, where you can 'saw' your wood into timber")
        ]
    )

    connect(forest, sawmill, "south", desc_ab="a loud sawmill deep in the forest", desc_ba="a heavily wooded forest")

    # Woodshop — skilled crafting room for carpentry recipes
    from typeclasses.terrain.rooms.room_crafting import RoomCrafting
    woodshop = create_object(
        RoomCrafting,
        key="Woodshop",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("crafting_type", "woodshop"),
            ("mastery_level", 1),  # BASIC
            ("craft_cost", 2),
            ("desc", "A small woodshop with tools of every kind arranged around the walls and benches."),
        ]
    )

    connect(sawmill, woodshop, "south", desc_ab="a small woodshop", desc_ba="a sawmill deep in the forest")


    ##########################
    # cotton area
    ##########################

    cotton = create_object(
        RoomHarvesting,
        key="Cotton Field",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("resource_id", 10),
            ("resource_count", 20),
            ("harvest_height", 0),
            ("abundance_threshold", 5),
            ("harvest_command", "harvest"),
            ("desc_abundant", "Rows of cotton plants stretch across the field, their white bolls bursting open in the warm sun. There is plenty to 'harvest''."),
            ("desc_scarce", "Most of the cotton has already been picked. A few scattered bolls cling to their stems awaiting 'harvest'."),
            ("desc_depleted", "The cotton field has been picked clean. Only bare stalks remain, swaying in the breeze."),
        ]
    )

    connect(dt3, cotton, "south", desc_ab="cotton field", desc_ba="a small dirt track")

    textile_mill = create_object(
        RoomProcessing,
        key="Textile Mill",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("processing_type", "textilemill"),
            ("process_cost", 1),
            ("recipes", [{"inputs": {10: 1}, "output": 11, "amount": 1, "cost": 1}]),
            ("desc", "A textile mill, where you can 'weave' your cotton into cloth")
        ]
    )

    connect(cotton, textile_mill, "south", desc_ab="a textile mill", desc_ba="cotton field")

    tailor = create_object(
        RoomCrafting,
        key="Tailor",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("crafting_type", "tailor"),
            ("mastery_level", 1),  # BASIC
            ("craft_cost", 2),
            ("desc", "An industrious tailor shop where cloth is made into "
                     "clothes and other finished products. Type 'recipes' "
                     "to see what you can craft."),
        ]
    )

    connect(textile_mill, tailor, "south", desc_ab="a tailors shop", desc_ba="a textile mill")


    #################
    ## leatherwork branch
    #################

    wolves = create_object(
        RoomBase,
        key="Wolves Den",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("allow_combat", True),
            ("desc", "A dark cavern where the Wolf pack rests when not hunting")
        ]
    )
    wolves.tags.add("deep_woods", category="mob_area")
    wolves.tags.add("wolves_den", category="mob_area")

    connect(dt5, wolves, "north", desc_ab="wolves den", desc_ba="a small dirt track")


    #################
    ## 3x3 woods area (east of wolves den) — combat / mob AI testing
    #################

    woods_descs = {
        "nw": "Dense woodland stretches in every direction. Gnarled oaks crowd together, their canopy filtering the light to a dim green haze. The ground is thick with fallen leaves.",
        "n":  "A narrow game trail winds between towering pines. Claw marks score the bark of several trees. Something large has passed through here recently.",
        "ne": "The woods thin slightly at this rocky outcrop. Boulders jut from the earth between the trees, offering cover — or concealment.",
        "w":  "Thick undergrowth chokes the forest floor here. Brambles snag at your clothing and visibility is poor. You can hear rustling in the brush.",
        "c":  "A small clearing in the heart of the woods. Shafts of light pierce the canopy above. The grass is flattened in places — something beds down here.",
        "e":  "The trees grow close together here, their roots tangling across the path. The air is still and heavy with the scent of damp earth and pine.",
        "sw": "A shallow stream trickles through the woods, its banks muddy with animal tracks. The water is clear but cold.",
        "s":  "Fallen trees create a natural barricade across the forest floor. You can clamber over them, but it slows your progress.",
        "se": "The forest floor slopes downward here into a mossy hollow. Mushrooms cluster around the base of rotting stumps.",
    }

    # Create 3x3 grid of rooms
    woods = {}
    for key, desc in woods_descs.items():
        woods[key] = create_object(
            RoomBase,
            key=f"Deep Woods",
            attributes=[
                ("max_height", 0),
                ("max_depth", 0),
                ("allow_combat", True),
                ("desc", desc),
            ]
        )
        woods[key].tags.add("deep_woods", category="mob_area")

    # Connect wolves den → woods west-centre
    connect(wolves, woods["w"], "east", desc_ab="deep woods", desc_ba="wolves den")

    # Horizontal connections (west ↔ centre ↔ east)
    for row, (left, mid, right) in [
        ("north", ("nw", "n", "ne")),
        ("mid",   ("w",  "c", "e")),
        ("south", ("sw", "s", "se")),
    ]:
        connect(woods[left], woods[mid], "east", desc_ab="deep woods", desc_ba="deep woods")
        connect(woods[mid], woods[right], "east", desc_ab="deep woods", desc_ba="deep woods")

    # Vertical connections (north ↔ mid ↔ south)
    for col, (top, mid, bot) in [
        ("west",   ("nw", "w",  "sw")),
        ("centre", ("n",  "c",  "s")),
        ("east",   ("ne", "e",  "se")),
    ]:
        connect(woods[top], woods[mid], "south", desc_ab="deep woods", desc_ba="deep woods")
        connect(woods[mid], woods[bot], "south", desc_ab="deep woods", desc_ba="deep woods")

    tannery = create_object(
        RoomProcessing,
        key="Tannery",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("processing_type", "tannery"),
            ("process_cost", 1),
            ("recipes", [{"inputs": {8: 1}, "output": 9, "amount": 1, "cost": 1}]),
            ("desc", "A smelly tannery where you can 'tan' a hide into leather")
        ]
    )

    connect(wolves, tannery, "north", desc_ab="a smelly tannery", desc_ba="wolves den")

    leathershop = create_object(
        RoomCrafting,
        key="Leathershop",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("crafting_type", "leathershop"),
            ("mastery_level", 1),  # BASIC
            ("craft_cost", 2),
            ("desc", "A grizzled old leatherworker labours away here making leather goods.")
        ]
    )

    connect(tannery, leathershop, "north", desc_ab="a leathershop", desc_ba="a smelly tannery")


    ##########################
    # cemetery
    ##########################

    cemetery = create_object(
        RoomCemetery,
        key="Cemetery",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("bind_cost", 1),
        ]
    )

    connect(dt4, cemetery, "north", desc_ab="a quiet cemetery", desc_ba="a small dirt track")


    ##########################
    # metals / blacksmithing area
    ##########################

    smelter = create_object(
        RoomProcessing,
        key="smelter",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("processing_type", "smelter"),
            ("process_cost", 1),
            ("recipes", [
                {"inputs": {4: 1}, "output": 5, "amount": 1, "cost": 1},      # Iron Ore → Iron Ingot
                {"inputs": {23: 1}, "output": 24, "amount": 1, "cost": 1},     # Copper Ore → Copper Ingot
                {"inputs": {25: 1}, "output": 26, "amount": 1, "cost": 1},     # Tin Ore → Tin Ingot
                {"inputs": {27: 1}, "output": 28, "amount": 1, "cost": 1},     # Lead Ore → Lead Ingot
                {"inputs": {30: 1}, "output": 31, "amount": 1, "cost": 1},     # Silver Ore → Silver Ingot
                {"inputs": {24: 1, 26: 1}, "output": 32, "amount": 1, "cost": 1},  # Copper + Tin → Bronze
                {"inputs": {26: 1, 28: 1}, "output": 29, "amount": 1, "cost": 1},  # Tin + Lead → Pewter
            ]),
            ("desc", "The roaring furnace in this smelter can 'smelt' ores into ingots and forge alloys. Type 'rates' to see what can be smelted.")
        ]
    )

    connect(dt4, smelter, "south", desc_ab="a hot smelter", desc_ba="a small dirt track")

    blacksmith = create_object(
        RoomCrafting,
        key="blacksmith",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("crafting_type", "smithy"),
            ("mastery_level", 1),  # BASIC
            ("craft_cost", 2),
            ("desc", "A blacksmith shop where you can 'forge' metal ingots into weapons, armour and other metal items. Type 'recipes' to see what you can craft.")
        ]
    )

    connect(smelter, blacksmith, "west", desc_ab="a blacksmith", desc_ba="smelter")

    jeweller = create_object(
        RoomCrafting,
        key="Jeweller",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("crafting_type", "jeweller"),
            ("mastery_level", 1),  # BASIC
            ("craft_cost", 2),
            ("desc", "A jeweller's workshop with delicate tools, small anvils, and "
                     "a charcoal forge for melting metal."),
        ]
    )

    connect(smelter, jeweller, "east", desc_ab="a jewellers workshop", desc_ba="smelter")

    # ── Mine Shaft — N-S corridor from smelter ──────────────────────────
    # Layout: Smelter → Mine Entrance → Ore Passage → Deep Passage
    #         → Gem Cavern → Diamond Mine (dead end)
    # Harvesting rooms branch east/west off the corridor.

    mine_entrance = create_object(
        RoomBase,
        key="Mine Entrance",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "Rough-hewn timber props support the entrance to the mine. "
                     "The passage descends south into darkness. Tunnels branch "
                     "east and west, and the glow of the smelter is visible to the north."),
        ]
    )
    connect(smelter, mine_entrance, "south", desc_ab="a mine entrance", desc_ba="the smelter")

    # -- East: Iron Mine (resource 4) --
    iron_mine = create_object(
        RoomHarvesting,
        key="Iron Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 4), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Veins of dark iron ore glint in the torchlight, streaking through the rough stone walls. There is plenty of ore here to 'mine'."),
            ("desc_scarce", "Most of the easily accessible ore has been chipped away. A few veins of iron still show here to 'mine'."),
            ("desc_depleted", "The mine walls are bare — every vein of iron has been exhausted. It will take time for new deposits to be exposed."),
        ]
    )
    connect(mine_entrance, iron_mine, "east", desc_ab="an iron mine", desc_ba="mine entrance")

    # -- West: Coal Mine (resource 36) --
    coal_mine = create_object(
        RoomHarvesting,
        key="Coal Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 36), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Thick seams of black coal run through the walls, leaving dark smudges on everything. There is plenty of coal to 'mine'."),
            ("desc_scarce", "Most of the coal has been hacked away. A few dark seams remain here to 'mine'."),
            ("desc_depleted", "The coal seam is exhausted — nothing but bare rock and coal dust. It will take time for new deposits to be exposed."),
        ]
    )
    connect(mine_entrance, coal_mine, "west", desc_ab="a coal mine", desc_ba="mine entrance")

    # ── Ore Passage ──────────────────────────────────────────────────
    ore_passage = create_object(
        RoomBase,
        key="Ore Passage",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("desc", "The passage narrows as it runs deeper south. Pickaxe marks "
                     "scar the walls and the air grows warmer. Tunnels branch east and west."),
        ]
    )
    connect(mine_entrance, ore_passage, "south", desc_ab="a deeper passage", desc_ba="the mine entrance")

    # -- East: Copper Mine (resource 23) --
    copper_mine = create_object(
        RoomHarvesting,
        key="Copper Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 23), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Green-streaked rock gives way to rich veins of native copper. There is plenty of copper ore to 'mine'."),
            ("desc_scarce", "Most of the copper has been extracted. A few greenish veins remain here to 'mine'."),
            ("desc_depleted", "The copper vein is spent — nothing but bare rock remains. It will take time for new deposits to be exposed."),
        ]
    )
    connect(ore_passage, copper_mine, "east", desc_ab="a copper mine", desc_ba="the ore passage")

    # -- West: Tin Mine (resource 25) --
    tin_mine = create_object(
        RoomHarvesting,
        key="Tin Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 25), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Dark, heavy veins of tin ore cut through the rock with a dull metallic sheen. There is plenty to 'mine'."),
            ("desc_scarce", "Most of the tin has been chipped away. A few dull veins remain here to 'mine'."),
            ("desc_depleted", "The tin deposits are exhausted — only bare stone remains. It will take time for new deposits to be exposed."),
        ]
    )
    connect(ore_passage, tin_mine, "west", desc_ab="a tin mine", desc_ba="the ore passage")

    # ── Deep Passage ─────────────────────────────────────────────────
    deep_passage = create_object(
        RoomBase,
        key="Deep Passage",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("desc", "The air is stale and hot this deep underground. Water drips "
                     "from the ceiling and the flicker of distant torches barely "
                     "illuminates the passage. Tunnels branch east and west."),
        ]
    )
    connect(ore_passage, deep_passage, "south", desc_ab="a deep passage", desc_ba="the ore passage")

    # -- East: Lead Mine (resource 27) --
    lead_mine = create_object(
        RoomHarvesting,
        key="Lead Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 27), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Dense, bluish-grey deposits of lead ore line the walls of this cramped tunnel. There is plenty to 'mine'."),
            ("desc_scarce", "Most of the lead has been dug out. A few dense grey veins remain here to 'mine'."),
            ("desc_depleted", "The lead deposits are exhausted — only bare rock remains. It will take time for new deposits to be exposed."),
        ]
    )
    connect(deep_passage, lead_mine, "east", desc_ab="a lead mine", desc_ba="the deep passage")

    # -- West: Silver Mine (resource 30) --
    silver_mine = create_object(
        RoomHarvesting,
        key="Silver Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 30), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Pale veins of native silver thread through the dark rock, catching the torchlight. There is plenty of silver ore to 'mine'."),
            ("desc_scarce", "Most of the silver has been extracted. A few pale veins still glint here to 'mine'."),
            ("desc_depleted", "The silver vein is spent — the rock walls are bare. It will take time for new deposits to be exposed."),
        ]
    )
    connect(deep_passage, silver_mine, "west", desc_ab="a silver mine", desc_ba="the deep passage")

    # ── Gem Cavern ───────────────────────────────────────────────────
    gem_cavern = create_object(
        RoomBase,
        key="Gem Cavern",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("desc", "The passage opens into a natural cavern. Crystalline formations "
                     "jut from the walls, catching the torchlight in dazzling prisms. "
                     "Tunnels branch east and west, and a narrow crack leads further south."),
        ]
    )
    connect(deep_passage, gem_cavern, "south", desc_ab="a glittering cavern", desc_ba="the deep passage")

    # -- East: Ruby Mine (resource 33) --
    ruby_mine = create_object(
        RoomHarvesting,
        key="Ruby Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 33), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Deep red crystals glint from pockets in the rock, catching the light like frozen flames. There are plenty of rubies to 'mine'."),
            ("desc_scarce", "Most of the rubies have been prised free. A few red crystals still glint in the rock to 'mine'."),
            ("desc_depleted", "The ruby deposits are exhausted — only empty sockets remain in the rock. It will take time for new crystals to be exposed."),
        ]
    )
    connect(gem_cavern, ruby_mine, "east", desc_ab="a ruby mine", desc_ba="the gem cavern")

    # -- West: Emerald Mine (resource 34) --
    emerald_mine = create_object(
        RoomHarvesting,
        key="Emerald Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 34), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "Brilliant green crystals cluster in the dark rock, glowing faintly in the torchlight. There are plenty of emeralds to 'mine'."),
            ("desc_scarce", "Most of the emeralds have been chiselled out. A few green crystals remain here to 'mine'."),
            ("desc_depleted", "The emerald deposits are exhausted — only bare rock and empty sockets remain. It will take time for new crystals to be exposed."),
        ]
    )
    connect(gem_cavern, emerald_mine, "west", desc_ab="an emerald mine", desc_ba="the gem cavern")

    # ── Diamond Mine — deepest point, dead end ───────────────────────
    diamond_mine = create_object(
        RoomHarvesting,
        key="Diamond Mine",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 35), ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "mine"),
            ("desc_abundant", "The passage ends in a cramped chamber of impossibly hard rock. Tiny, flawless crystals catch the torchlight like trapped stars. There are diamonds to 'mine'."),
            ("desc_scarce", "Most of the diamonds have been painstakingly extracted. A few tiny crystals still glint in the rock to 'mine'."),
            ("desc_depleted", "The diamond seam is exhausted — nothing but scarred, impenetrable rock remains. It will take time for new crystals to be exposed."),
        ]
    )
    connect(gem_cavern, diamond_mine, "south", desc_ab="a narrow crack leading deeper", desc_ba="the gem cavern")

    ##########################
    # alchemy area
    ##########################

    apothecary = create_object(
        RoomCrafting,
        key="Apothecary",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("crafting_type", "apothecary"),
            ("mastery_level", 1),
            ("craft_cost", 2),
            ("desc", "An apothecary lined with shelves of jars and vials. You can 'brew' potions here if you know the recipes."),
        ],
    )

    connect(dt5, apothecary, "south", desc_ab="an apothecary", desc_ba="a small dirt track")

    # -- South of apothecary: Distillery (processing room) --
    distillery = create_object(
        RoomProcessing,
        key="Distillery",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("processing_type", "apothecary"),
            ("process_cost", 1),
            ("recipes", [{"inputs": {12: 1}, "output": 13, "amount": 1, "cost": 1}]),
            ("desc", "A small distillery with copper stills and glass alembics. You can 'distill' raw ingredients into essences here."),
        ],
    )
    connect(apothecary, distillery, "south", desc_ab="a distillery", desc_ba="the apothecary")

    # -- East of distillery: Moonpetal Meadow (resource 12) --
    moonpetal_meadow = create_object(
        RoomHarvesting,
        key="Moonpetal Meadow",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 12), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Silver-white moonpetals carpet this moonlit meadow, their luminous petals swaying gently. There are plenty to 'gather'."),
            ("desc_scarce", "Most of the moonpetals have been picked. A few luminous blooms remain to 'gather'."),
            ("desc_depleted", "The meadow is bare — every moonpetal has been gathered. They will need time to regrow."),
        ],
    )
    connect(distillery, moonpetal_meadow, "east", desc_ab="a moonlit meadow of silver-white flowers", desc_ba="the distillery")

    # -- West of distillery: Bloodmoss Bog (resource 14) --
    bloodmoss_bog = create_object(
        RoomHarvesting,
        key="Bloodmoss Bog",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 14), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Dark crimson moss clings to every rock and fallen log in this damp bog. Clumps of bloodmoss are plentiful to 'gather'."),
            ("desc_scarce", "The bog has been mostly picked over. A few patches of dark crimson moss remain to 'gather'."),
            ("desc_depleted", "The bog is picked clean — not a trace of bloodmoss remains. It will need time to regrow."),
        ],
    )
    connect(distillery, bloodmoss_bog, "west", desc_ab="a dark, damp bog", desc_ba="the distillery")

    # -- South of distillery: Windroot Hollow (resource 15) --
    windroot_hollow = create_object(
        RoomHarvesting,
        key="Windroot Hollow",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 15), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Gnarled windroot grows wild in this sheltered hollow, its pale tendrils dancing in unseen breezes. Plenty of roots to 'gather'."),
            ("desc_scarce", "Most of the windroot has been uprooted. A few pale tendrils remain to 'gather'."),
            ("desc_depleted", "The hollow is bare — every windroot has been dug up. They will need time to regrow."),
        ],
    )
    connect(distillery, windroot_hollow, "south", desc_ab="a sheltered hollow", desc_ba="the distillery")

    # -- Herb passage extending south --
    overgrown_path = create_object(
        RoomBase,
        key="Overgrown Path",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("desc", "A narrow, overgrown path winds south through dense undergrowth. The air is thick with the scent of herbs and damp earth."),
        ],
    )
    connect(windroot_hollow, overgrown_path, "south", desc_ab="an overgrown path", desc_ba="a sheltered hollow")

    # -- East of overgrown path: Arcane Ruins (resource 16 — Arcane Dust) --
    arcane_ruins = create_object(
        RoomHarvesting,
        key="Arcane Ruins",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 16), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Crumbling stone arches shimmer with residual magic. Fine arcane dust coats every surface, ready to 'gather'."),
            ("desc_scarce", "Most of the arcane dust has been swept up. A few sparkling patches remain to 'gather'."),
            ("desc_depleted", "The ruins are scoured clean — not a pinch of arcane dust remains. It will take time for more to accumulate."),
        ],
    )
    connect(overgrown_path, arcane_ruins, "east", desc_ab="crumbling arcane ruins", desc_ba="an overgrown path")

    # -- West of overgrown path: Mushroom Grotto (resource 17 — Ogre's Cap) --
    mushroom_grotto = create_object(
        RoomHarvesting,
        key="Mushroom Grotto",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 17), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Fat, bulbous mushrooms with mottled grey caps crowd the damp grotto floor. There are plenty of ogre's caps to 'gather'."),
            ("desc_scarce", "Most of the mushrooms have been picked. A few ogre's caps remain in the shadows to 'gather'."),
            ("desc_depleted", "The grotto floor is bare — every ogre's cap has been picked. They will need time to regrow."),
        ],
    )
    connect(overgrown_path, mushroom_grotto, "west", desc_ab="a damp mushroom grotto", desc_ba="an overgrown path")

    # -- Continue south --
    tangled_path = create_object(
        RoomBase,
        key="Tangled Path",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("desc", "Twisted vines and thorny brambles crowd a narrow path winding further south through wild herb gardens."),
        ],
    )
    connect(overgrown_path, tangled_path, "south", desc_ab="a tangled path", desc_ba="an overgrown path")

    # -- East of tangled path: Vipervine Thicket (resource 18) --
    vipervine_thicket = create_object(
        RoomHarvesting,
        key="Vipervine Thicket",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 18), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Sinuous green tendrils writhe slowly through the undergrowth, coiling around branches. Plenty of vipervine to 'gather'."),
            ("desc_scarce", "Most of the vipervine has been cut away. A few tendrils still slither through the brush to 'gather'."),
            ("desc_depleted", "The thicket has been stripped clean — every tendril of vipervine has been taken. They will need time to regrow."),
        ],
    )
    connect(tangled_path, vipervine_thicket, "east", desc_ab="a writhing thicket", desc_ba="a tangled path")

    # -- West of tangled path: Ironbark Grove (resource 19) --
    ironbark_grove = create_object(
        RoomHarvesting,
        key="Ironbark Grove",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 19), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Dark, iron-hard trees stand sentinel in this ancient grove. Their metallic bark peels in thick strips, ready to 'gather'."),
            ("desc_scarce", "Most of the ironbark has been stripped. A few thick strips remain to 'gather'."),
            ("desc_depleted", "The grove trees are stripped bare — not a scrap of ironbark remains. It will take time for the bark to regrow."),
        ],
    )
    connect(tangled_path, ironbark_grove, "west", desc_ab="a grove of iron-dark trees", desc_ba="a tangled path")

    # -- Continue south --
    shaded_path = create_object(
        RoomBase,
        key="Shaded Path",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("desc", "Thick canopy overhead casts this narrow path in perpetual shade. Strange fungi and herbs thrive in the dappled gloom."),
        ],
    )
    connect(tangled_path, shaded_path, "south", desc_ab="a shaded path", desc_ba="a tangled path")

    # -- East of shaded path: Mindcap Hollow (resource 20) --
    mindcap_hollow = create_object(
        RoomHarvesting,
        key="Mindcap Hollow",
        attributes=[
            ("max_height", 0), ("max_depth", 0),
            ("resource_id", 20), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Iridescent blue-capped mushrooms cluster in this damp hollow, pulsing faintly with inner light. Plenty of mindcap to 'gather'."),
            ("desc_scarce", "Most of the mindcap mushrooms have been picked. A few luminous caps remain in the shadows to 'gather'."),
            ("desc_depleted", "The hollow is bare — every mindcap has been taken. They will need time to regrow."),
        ],
    )
    connect(shaded_path, mindcap_hollow, "east", desc_ab="a hollow glowing with blue mushrooms", desc_ba="a shaded path")

    # -- West of shaded path: Sage Garden (resource 21) --
    sage_garden = create_object(
        RoomHarvesting,
        key="Sage Garden",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 21), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Silvery-green sage bushes fill this sheltered garden, their fragrant leaves rustling softly. There are plenty of sage leaves to 'gather'."),
            ("desc_scarce", "Most of the sage has been picked. A few fragrant sprigs remain to 'gather'."),
            ("desc_depleted", "The garden has been picked clean — not a leaf of sage remains. It will take time to regrow."),
        ],
    )
    connect(shaded_path, sage_garden, "west", desc_ab="a fragrant sage garden", desc_ba="a shaded path")

    # -- South of shaded path: Siren's Pool (resource 22) --
    sirens_pool = create_object(
        RoomHarvesting,
        key="Siren's Pool",
        attributes=[
            ("max_height", 1), ("max_depth", 0),
            ("resource_id", 22), ("harvest_height", 0),
            ("resource_count", 20), ("abundance_threshold", 5),
            ("harvest_command", "gather"),
            ("desc_abundant", "Luminous pink petals float on the surface of a still, enchanted pool. Siren petals drift to the edges, ready to 'gather'."),
            ("desc_scarce", "Most of the siren petals have been collected. A few pink petals still float on the pool to 'gather'."),
            ("desc_depleted", "The pool's surface is clear — every siren petal has been gathered. They will need time to drift back."),
        ],
    )
    connect(shaded_path, sirens_pool, "south", desc_ab="an enchanted pool", desc_ba="a shaded path")


    #################
    ## guild branch
    #################

    guild_square = create_object(
        RoomBase,
        key="Guild Square",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "A big open square with guild halls occupying the buildings on all sides")
        ]
    )

    connect(dt1, guild_square, "north", desc_ab="guild square", desc_ba="a small dirt track")

    warriors_guild_entrance = create_object(
        RoomBase,
        key="Warriors Guild",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "The entrance to the warriors guild")
        ]
    )

    connect(guild_square, warriors_guild_entrance, "west", desc_ab="Warriors Guild", desc_ba="guild square")

    guildmasters_chamber = create_object(
        RoomBase,
        key="Guildmasters Chamber",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A square chamber lined with weapon racks and battle trophies. "
             "Scarred shields and notched blades adorn the stone walls — each "
             "one a testament to a warrior who earned their place in the guild. "
             "A heavy oak desk sits at the far end, where the Warlord conducts "
             "guild business.")
        ]
    )

    connect(warriors_guild_entrance, guildmasters_chamber, "north", desc_ab="Guildmasters Chamber", desc_ba="Warriors Guild")

    thieves_guild_entrance = create_object(
        RoomBase,
        key="Thieves Guild Entrance",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "The entrance to the thieves guild")
        ]
    )

    connect(guild_square, thieves_guild_entrance, "down", desc_ab="Thieves Guild", desc_ba="guild square")

    mages_guild_entrance = create_object(
        RoomBase,
        key="Mages Guild Entrance",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "The entrance to the mages guild")
        ]
    )

    connect(guild_square, mages_guild_entrance, "east", desc_ab="Mages Guild", desc_ba="guild square")

    wizards_workshop = create_object(
        RoomCrafting,
        key="Wizard's Workshop",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("crafting_type", "wizards_workshop"),
            ("mastery_level", 1),
            ("craft_cost", 3),
            ("desc",
             "A vaulted chamber lined with arcane workbenches and softly "
             "glowing crystals. Shelves of reagents and half-finished "
             "enchantments line the walls. The air hums with residual magic."),
        ]
    )

    connect(mages_guild_entrance, wizards_workshop, "north", desc_ab="Wizard's Workshop", desc_ba="Mages Guild")

    clerics_guild_entrance = create_object(
        RoomBase,
        key="Temple Entrance",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "The entrance to the temple")
        ]
    )

    connect(guild_square, clerics_guild_entrance, "north", desc_ab="temple", desc_ba="guild square")

    temple_sanctum = create_object(
        RoomBase,
        key="Temple Sanctum",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A serene chamber bathed in soft golden light from stained glass "
             "windows. Prayer benches line the walls and the air carries the "
             "faint scent of incense. Sacred texts rest on a lectern nearby."),
        ]
    )

    connect(clerics_guild_entrance, temple_sanctum, "east", desc_ab="Temple Sanctum", desc_ba="Temple Entrance")

    #################
    ## marketplace branch
    #################

    market_square = create_object(
        RoomBase,
        key="Market Square",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "An wide square with shops and merchants on all sides")
        ]
    )

    connect(dt2, market_square, "north", desc_ab="market square", desc_ba="a small dirt track")

    shop_west = create_object(
        RoomBase,
        key="General Store",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "Shelves and barrels line the walls of this well-stocked "
             "general store. Sacks of grain sit beside bundles of flour and "
             "neatly wrapped loaves. A slate board behind the counter lists "
             "the day's prices in chalk.")
        ]
    )

    connect(market_square, shop_west, "west", desc_ab="a general store", desc_ba="market square")

    shop_east = create_object(
        RoomBase,
        key="shop east",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "shop 2 displays their wares")
        ]
    )

    connect(market_square, shop_east, "east", desc_ab="shop east", desc_ba="market square")

    shop_north = create_object(
        RoomBase,
        key="shop north",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", "shop 3 displays their wares")
        ]
    )

    connect(market_square, shop_north, "north", desc_ab="shop north", desc_ba="market square")


    #################
    ## Inn
    #################

    inn_desc = (
    "\nWarm firelight dances across polished wooden beams and well-worn floors."
    "\nA sturdy bar stretches along one wall, with a cheerful innkeeper ready"
    "\nto serve food, drink, and a comfortable room for the night."
    "\nA broad staircase leads up to guest chambers, while a roaring hearth"
    "\ncrackles invitingly at the heart of the common room."
    "\n\n|c--- Menu ---|n"
    "\n|wstew|n - a warm bowl of stew with lumps of unknown meat"
    "\n|wale|n - a warm bowl of stew with lumps of unknown meat"
    )

    inn = create_object(
        RoomInn,
        key="inn",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", inn_desc)
        ]
    )

    connect(dt3, inn, "north", desc_ab="The Gilded Griffin Inn", desc_ba="a small dirt track")


    #################
    ## dt6 and dt7 — extend the dirt track
    #################

    dt6 = create_object(
        RoomBase,
        key="dirt track 6",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this east west dirt track connects all the  economic test rooms")
        ]
    )

    connect(dt5, dt6, "east", desc_ab="a small dirt track", desc_ba="a small dirt track")

    dt7 = create_object(
        RoomBase,
        key="dirt track 7",
        attributes=[
            ("max_height", 1),
            ("max_depth", 0),
            ("desc", "this east west dirt track connects all the  economic test rooms")
        ]
    )

    connect(dt6, dt7, "east", desc_ab="a small dirt track", desc_ba="a small dirt track")

    #################
    ## bank
    #################

    bank_desc = (
    "\nThe marble floors gleam under the soft light of enchanted lanterns."
    "\nTellers stand behind ornate iron grilles, ready to assist with your"
    "\nfinancial needs. A large vault door dominates the far wall."
    "\n\n|c--- Availble Commands ---|n"
    "\n|wwithdraw|n - take items out of the bank (wallet to character)"
    "\n|wdeposit|n  - put items into the bank (character to wallet)"
    "\n|wbalance|n  - list items available for withdrawl"
    )

    bank = create_object(
        RoomBank,
        key="bank",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc", bank_desc)
        ]
    )

    connect(dt7, bank, "east", desc_ab="First Millholm Community Bank", desc_ba="a small dirt track")

    #############################
    ## trapped passage (south of dt7)
    #############################

    # Room 1 — Passage entrance (plain room with warning sign)
    trap_entrance = create_object(
        RoomBase,
        key="passage entrance",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A narrow stone passage stretches south into darkness. The walls"
             "\nare scarred with scorch marks and old bloodstains. A weathered"
             "\nsign is nailed to the wall near the entrance."
             "\n\n|rThis area contains traps for testing the trap system.|n"
             "\nUse |wsearch|n to detect traps, |wdisarm|n to disarm them.")
        ]
    )

    sign = create_object(WorldSign, key="a warning sign", location=trap_entrance)
    sign.sign_text = (
        " DANGER - TRAPS AHEAD\n"
        " Proceed with caution.\n"
        " Thieves welcome."
    )
    sign.sign_style = "wall"

    connect(dt7, trap_entrance, "south",
            desc_ab="a dark passage",
            desc_ba="a small dirt track")

    # Room 2 — Narrow corridor (behind a trapped door)
    trap_corridor = create_object(
        RoomBase,
        key="narrow corridor",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A claustrophobic stone corridor. The air smells faintly of"
             "\nalchemy reagents. The floor ahead looks suspiciously clean.")
        ]
    )

    # Trapped door pair between entrance and corridor (poison needle trap)
    trap_door_ab = create_object(
        TrapDoor,
        key="a reinforced door",
        location=trap_entrance,
        destination=trap_corridor,
    )
    trap_door_ab.set_direction("south")
    trap_door_ab.door_name = "door"
    trap_door_ab.closed_desc = "A reinforced iron door blocks the passage south."
    trap_door_ab.open_desc = "Through the open door, a narrow corridor stretches south."
    trap_door_ab.is_trapped = True
    trap_door_ab.trap_armed = True
    trap_door_ab.trap_damage_dice = "1d6"
    trap_door_ab.trap_damage_type = "poison"
    trap_door_ab.trap_find_dc = 10
    trap_door_ab.trap_disarm_dc = 10
    trap_door_ab.trap_description = "a poison needle trap"

    trap_door_ba = create_object(
        TrapDoor,
        key="a reinforced door",
        location=trap_corridor,
        destination=trap_entrance,
    )
    trap_door_ba.set_direction("north")
    trap_door_ba.door_name = "door"
    trap_door_ba.closed_desc = "A reinforced iron door blocks the passage north."
    trap_door_ba.open_desc = "Through the open door, the passage entrance lies north."

    from typeclasses.terrain.exits.exit_door import ExitDoor
    ExitDoor.link_door_pair(trap_door_ab, trap_door_ba)

    # Room 3 — Pressure plate chamber (pressure plate + trapped chest)
    trap_chamber = create_object(
        PressurePlateRoom,
        key="pressure plate chamber",
        attributes=[
            ("max_height", 0),
            ("max_depth", 0),
            ("desc",
             "A square stone chamber with an unusually smooth floor. Faint"
             "\ncracks outline individual flagstones — some of them look like"
             "\nthey could shift under weight. An old chest sits against the"
             "\nfar wall.")
        ]
    )
    trap_chamber.is_trapped = True
    trap_chamber.trap_armed = True
    trap_chamber.trap_damage_dice = "2d6"
    trap_chamber.trap_damage_type = "fire"
    trap_chamber.trap_find_dc = 10
    trap_chamber.trap_disarm_dc = 10
    trap_chamber.trap_description = "a pressure plate"

    # Tripwire exit between corridor and chamber
    tripwire_ab = create_object(
        TripwireExit,
        key="south",
        location=trap_corridor,
        destination=trap_chamber,
    )
    tripwire_ab.set_direction("south")
    tripwire_ab.is_trapped = True
    tripwire_ab.trap_armed = True
    tripwire_ab.trap_damage_dice = "1d6"
    tripwire_ab.trap_damage_type = "piercing"
    tripwire_ab.trap_find_dc = 10
    tripwire_ab.trap_disarm_dc = 10
    tripwire_ab.trap_description = "a tripwire"

    # Return exit from chamber to corridor (plain, no trap)
    connect_back = create_object(
        "typeclasses.terrain.exits.exit_vertical_aware.ExitVerticalAware",
        key="narrow corridor",
        location=trap_chamber,
        destination=trap_corridor,
    )
    connect_back.set_direction("north")

    # Trapped chest in the chamber (acid trap)
    trapped_chest = create_object(
        TrapChest,
        key="old chest",
        location=trap_chamber,
    )
    trapped_chest.db.desc = "A battered wooden chest. The lock mechanism looks oddly complex."
    trapped_chest.is_trapped = True
    trapped_chest.trap_armed = True
    trapped_chest.trap_damage_dice = "1d6"
    trapped_chest.trap_damage_type = "acid"
    trapped_chest.trap_find_dc = 10
    trapped_chest.trap_disarm_dc = 10
    trapped_chest.trap_description = "an acid vial trap"
    trapped_chest.is_open = False

    trap_passage_rooms = [trap_entrance, trap_corridor, trap_chamber]

    ##########################
    # Zone and District tags
    ##########################

    # All rooms in this script belong to the same zone
    all_rooms = [
        dt1, dt2, dt3, dt4, dt5, dt6, dt7,
        guild_square, warriors_guild_entrance, guildmasters_chamber,
        thieves_guild_entrance, mages_guild_entrance, wizards_workshop,
        clerics_guild_entrance, temple_sanctum,
        market_square, shop_west, shop_east, shop_north,
        wheat_farm, windmill, bakery,
        forest, sawmill, woodshop,
        cotton, textile_mill, tailor,
        smelter, blacksmith, jeweller,
        mine_entrance, iron_mine, coal_mine, ore_passage, copper_mine,
        tin_mine, deep_passage, lead_mine, silver_mine,
        gem_cavern, ruby_mine, emerald_mine, diamond_mine,
        apothecary, distillery,
        moonpetal_meadow, bloodmoss_bog, windroot_hollow,
        overgrown_path, arcane_ruins, mushroom_grotto,
        tangled_path, vipervine_thicket, ironbark_grove,
        shaded_path, mindcap_hollow, sage_garden, sirens_pool,
        inn, cemetery, bank,
        wolves, tannery, leathershop,
    ] + list(woods.values()) + trap_passage_rooms

    for room in all_rooms:
        room.tags.add("test_economic_zone", category="zone")

    # --- Districts ---

    wolf_rooms = [wolves, tannery, leathershop] + list(woods.values())
    for room in wolf_rooms:
        room.tags.add("wolf_district", category="district")

    guild_rooms = [
        guild_square, warriors_guild_entrance, guildmasters_chamber,
        thieves_guild_entrance, mages_guild_entrance, wizards_workshop,
        clerics_guild_entrance, temple_sanctum,
    ]
    for room in guild_rooms:
        room.tags.add("guild_district", category="district")

    market_rooms = [market_square, shop_west, shop_east, shop_north]
    for room in market_rooms:
        room.tags.add("market_district", category="district")

    resource_rooms = [
        dt1, dt2, dt3, dt4, dt5, dt6, dt7,
        wheat_farm, windmill, bakery,
        forest, sawmill, woodshop,
        cotton, textile_mill, tailor,
        smelter, blacksmith, jeweller,
        mine_entrance, iron_mine, coal_mine, ore_passage, copper_mine,
        tin_mine, deep_passage, lead_mine, silver_mine,
        gem_cavern, ruby_mine, emerald_mine, diamond_mine,
        apothecary, distillery,
        moonpetal_meadow, bloodmoss_bog, windroot_hollow,
        overgrown_path, arcane_ruins, mushroom_grotto,
        tangled_path, vipervine_thicket, ironbark_grove,
        shaded_path, mindcap_hollow, sage_garden, sirens_pool,
        inn, cemetery,
    ]
    for room in resource_rooms:
        room.tags.add("resource_district", category="district")

    bank.tags.add("bank_district", category="district")

    # --- Terrain types ---

    rural_rooms = [
        dt1, dt2, dt3, dt4, dt5, dt6, dt7,
        wheat_farm, cotton,
    ]
    for room in rural_rooms:
        room.set_terrain(TerrainType.RURAL.value)

    forest_rooms = [
        forest, wolves, tannery, leathershop,
    ] + list(woods.values())
    for room in forest_rooms:
        room.set_terrain(TerrainType.FOREST.value)

    urban_rooms = [
        windmill, bakery, sawmill, woodshop,
        textile_mill, tailor,
        smelter, blacksmith, jeweller,
        guild_square, warriors_guild_entrance, guildmasters_chamber,
        thieves_guild_entrance, mages_guild_entrance, wizards_workshop,
        clerics_guild_entrance, temple_sanctum,
        market_square, shop_west, shop_east, shop_north,
        inn, bank, cemetery,
        apothecary, distillery,
    ]
    for room in urban_rooms:
        room.set_terrain(TerrainType.URBAN.value)

    underground_rooms = [
        mine_entrance, iron_mine, coal_mine, ore_passage, copper_mine,
        tin_mine, deep_passage, lead_mine, silver_mine,
        gem_cavern, ruby_mine, emerald_mine, diamond_mine,
        mushroom_grotto, mindcap_hollow,
    ] + trap_passage_rooms
    for room in underground_rooms:
        room.set_terrain(TerrainType.UNDERGROUND.value)

    # Herb gathering areas — rural/wilderness feel
    rural_herb_rooms = [
        moonpetal_meadow, bloodmoss_bog, windroot_hollow,
        overgrown_path, arcane_ruins,
        tangled_path, vipervine_thicket, ironbark_grove,
        shaded_path, sage_garden, sirens_pool,
    ]
    for room in rural_herb_rooms:
        room.set_terrain(TerrainType.FOREST.value)

    print("Test Economic Area Created")

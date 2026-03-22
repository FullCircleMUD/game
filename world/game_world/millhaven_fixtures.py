"""
Millhaven world fixtures — signs, monuments, fountains, and other
interactable objects placed into already-built rooms.

Called after all district builders have run, so rooms already exist.
Fixtures are WorldFixture/WorldSign objects that players can look at
but cannot pick up.

NOTE: Many former fixtures (fountain, oak tree, monument, notice board,
town signposts) have been converted to lightweight room details (the
`details` dict on each room). Only objects that genuinely need to be
full DB objects remain as fixtures here.

Usage:
    from world.game_world.millhaven_fixtures import place_millhaven_fixtures
    place_millhaven_fixtures(town_rooms, farm_rooms, woods_rooms, sewer_rooms)
"""

from evennia import create_object

from typeclasses.world_objects.base_fixture import WorldFixture
from typeclasses.world_objects.jobs_board import JobsBoard
from typeclasses.world_objects.sign import WorldSign


def place_millhaven_fixtures(town_rooms, farm_rooms, woods_rooms, sewer_rooms):
    """Place world fixtures into already-built Millhaven rooms."""
    print("[5] Placing world fixtures...")
    count = 0

    # ══════════════════════════════════════════════════════════════════
    # TOWN — Jobs board
    # ══════════════════════════════════════════════════════════════════

    jobs_board = create_object(
        JobsBoard,
        key="a weathered jobs board",
        location=town_rooms["sq_nw"],
        nohome=True,
    )
    jobs_board.db.desc = (
        "A large wooden board, its frame grey with weather. Handwritten "
        "notices are pinned and nailed into every available space — requests "
        "from townsfolk looking for a helping hand."
    )
    jobs_board.postings = [
        {
            "npc": "Bron the Baker",
            "title": "Flour Needed",
            "description": "I'm running low on flour. If you can bring me "
                           "some, I'll make it worth your while. — Bron",
        },
        {
            "npc": "Master Oakwright",
            "title": "Timber Delivery",
            "description": "The woodshop needs fresh timber. Good pay "
                           "for honest work. — Oakwright",
        },
        {
            "npc": "Elena Copperkettle",
            "title": "Cloth Needed URGENTLY",
            "description": "PLEASE if anyone can bring me 3 bolts of cloth "
                           "I will pay HANDSOMELY — wedding this weekend "
                           "— no time to explain — Elena",
        },
        {
            "npc": "Mara Brightwater",
            "title": "Moonpetal Needed",
            "description": "Fresh moonpetal required for a remedy. "
                           "Enquire at The Mortar and Pestle. — M.B.",
        },
        {
            "npc": "Old Hendricks",
            "title": "Bronze for the Forge",
            "description": "Need bronze ingots. Copper and tin from the "
                           "mine, smelted proper. Good pay. — Hendricks",
        },
    ]
    count += 1

    # ══════════════════════════════════════════════════════════════════
    # FARMS — Signs and fixtures
    # ══════════════════════════════════════════════════════════════════

    # Crossroads — signpost + mile marker
    crossroads_sign = create_object(
        WorldSign,
        key="a weathered signpost",
        location=farm_rooms["farm_road_crossroads"],
        nohome=True,
    )
    crossroads_sign.sign_text = "Millhaven East / Farms West"
    crossroads_sign.sign_style = "post"
    count += 1

    mile_marker = create_object(
        WorldFixture,
        key="a stone mile-marker",
        location=farm_rooms["farm_road_crossroads"],
        nohome=True,
    )
    mile_marker.db.desc = (
        "A squat stone pillar, barely knee-height, carved with the words "
        "'Millhaven 2 leagues'. Lichen has crept across the lettering, "
        "and the stone is chipped from years of cart wheels clipping its "
        "corner. A small snail traces a silver path across the top."
    )
    count += 1

    # Brightwater Farm track — farm sign
    bw_sign = create_object(
        WorldSign,
        key="a weathered wooden sign",
        location=farm_rooms["bw_track"],
        nohome=True,
    )
    bw_sign.sign_text = "Brightwater Farm — Finest Cotton in Millhaven"
    bw_sign.sign_style = "hanging"
    count += 1

    # Goldwheat Farm lane — farm sign
    gw_sign = create_object(
        WorldSign,
        key="a hand-painted sign",
        location=farm_rooms["gw_lane"],
        nohome=True,
    )
    gw_sign.sign_text = "Goldwheat Farm — Fresh Grain & Flour"
    gw_sign.sign_style = "hanging"
    count += 1

    # Windmill — millstone
    millstone = create_object(
        WorldFixture,
        key="a pair of millstones",
        location=farm_rooms["windmill"],
        nohome=True,
    )
    millstone.db.desc = (
        "Two massive circular stones, each as wide as a man is tall, "
        "grind against each other with a deep, resonant rumble. The upper "
        "stone turns slowly, driven by the great wooden gears connected "
        "to the windmill's sails. Wheat pours in through a hopper at the "
        "center and emerges as fine flour at the edges, carried away by "
        "a wooden chute into waiting sacks."
    )
    count += 1

    # Abandoned farmyard — rusted plough
    plough = create_object(
        WorldFixture,
        key="a rusted plough",
        location=farm_rooms["ab_yard"],
        nohome=True,
    )
    plough.db.desc = (
        "A heavy iron plough sits forgotten in the corner, its blade "
        "pitted with rust and its wooden handles crumbling. Ivy has "
        "wound its way through the frame, slowly pulling the implement "
        "into the earth. Whatever farmer once drove this plough through "
        "rich soil is long gone."
    )
    count += 1

    # ══════════════════════════════════════════════════════════════════
    # WOODS — Fixtures
    # ══════════════════════════════════════════════════════════════════

    # Sawmill — the great saw
    saw = create_object(
        WorldFixture,
        key="a great saw",
        location=woods_rooms["sawmill"],
        nohome=True,
    )
    saw.db.desc = (
        "An enormous iron-toothed saw blade, nearly six feet long, is "
        "mounted on a heavy wooden frame. A system of pulleys and gears "
        "drives it back and forth with tireless mechanical precision. "
        "Workers feed logs along a guide rail and the blade tears through "
        "them with a high-pitched shriek that can be heard throughout "
        "the surrounding forest. Fresh sawdust piles up beneath."
    )
    count += 1

    # Smelter — the forge
    forge = create_object(
        WorldFixture,
        key="a roaring forge",
        location=woods_rooms["smelter"],
        nohome=True,
    )
    forge.db.desc = (
        "A massive stone furnace dominates the center of the smelter, "
        "its belly glowing white-hot. Bellows the size of a horse pump "
        "air through clay pipes, and the heat is almost unbearable even "
        "from across the room. Crucibles of molten metal sit in racks "
        "nearby, their contents shimmering like liquid fire. Ingot molds "
        "of various sizes line the walls, some still warm from recent use."
    )
    count += 1

    # ══════════════════════════════════════════════════════════════════
    # SEWERS — Fixtures
    # ══════════════════════════════════════════════════════════════════

    # Blocked Grate — the grate itself
    grate = create_object(
        WorldFixture,
        key="a rusty iron grate",
        location=sewer_rooms["blocked_grate"],
        nohome=True,
    )
    grate.db.desc = (
        "A heavy iron grate is set into the stone wall, its bars thick "
        "with rust and mineral deposits. Through the gaps you can see "
        "daylight and hear the distant sounds of the town above — voices, "
        "cart wheels, a dog barking. The bars are far too close together "
        "to squeeze through, and the rust has welded the grate solidly "
        "into its frame. You're not getting through here."
    )
    count += 1

    # Thieves' Hall — a crude map
    thief_map = create_object(
        WorldFixture,
        key="a crude map",
        location=sewer_rooms["thieves_hall"],
        nohome=True,
    )
    thief_map.db.desc = (
        "A large piece of tanned leather is stretched across the wall, "
        "marked with charcoal and ink. It shows a rough layout of "
        "Millhaven's streets, with certain buildings circled and "
        "annotated in thieves' cant. Red marks indicate guard patrol "
        "routes, and small X's mark what might be hidden entrance points. "
        "Several pins hold scraps of parchment with notes — job details, "
        "perhaps, or marks for future heists."
    )
    count += 1

    # Shadow Mistress's Chamber — a lockbox
    lockbox = create_object(
        WorldFixture,
        key="a heavy iron lockbox",
        location=sewer_rooms["shadow_mistress_chamber"],
        nohome=True,
    )
    lockbox.db.desc = (
        "A squat iron box sits bolted to the floor beneath the desk, "
        "secured with three separate locks of increasing complexity. "
        "The metal is cold to the touch and engraved with warnings in "
        "thieves' cant that roughly translate to 'Touch this and die "
        "slowly.' Whatever the Shadow Mistress keeps in here, she does "
        "not want it found."
    )
    count += 1

    print(f"  Placed {count} world fixtures.")

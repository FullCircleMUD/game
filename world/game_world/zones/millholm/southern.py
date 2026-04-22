"""
Millholm Southern District — the countryside and Shadowsward beyond the south gate.

Builds ~24 rooms across five sections:
- Countryside (4 rooms): Countryside Road, Farmstead Fork, Bandit Holdfast,
  Bandit Camp
- Moonpetal Fields (7 rooms): Moonpetal Approach + 2x3 harvest grid
  (resource_id=12, gather command)
- Gnoll Territory (5 rooms): Wild Grasslands, Hunting Grounds, Ravaged
  Farmstead, Gnoll Camp, Gnoll Lookout
- Barrow Underground (5 rooms): Barrow Hill (hidden entrance), Barrow
  Entrance, Bone-Strewn Passage, Ancient Catacombs, Necromancer's Study
- Shadowsward (2 rooms): Southern Approach, Shadowsward Gate (zone exit)

The district has two entrances:
- North: from town_rooms["south_gate"] (wired in build_game_world.py)
- West: from farm_rooms["south_fork_end"] (wired in build_game_world.py)

The barrow entrance is hidden (is_hidden=True, find_dc=18) — players must
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
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from utils.exit_helpers import connect_bidirectional_exit, connect_bidirectional_door_exit


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
    rooms["farmstead_fork"].details = {
        "signpost": (
            "A rotting wooden post with a crossbar that once pointed "
            "in three directions. The painted text has weathered away "
            "to illegibility. Someone has scratched a crude skull into "
            "the wood — a warning, or a joke."
        ),
        "tracks": (
            "The trampled grass shows prints that are broad, clawed, "
            "and not human. They come from the south in groups of "
            "six or eight, mill around the fork, and retreat the "
            "same way. Gnoll raiding parties, scouting the road."
        ),
    }

    rooms["bandit_holdfast"] = create_object(
        RoomBase,
        key="Bandit Holdfast",
        attributes=[
            ("desc",
             "A ruined farmstead behind a crumbling stone wall, its "
             "buildings patched with stolen timber and canvas. What was "
             "once a respectable homestead has been turned into a rough "
             "fortification — the windows are boarded, the doorways "
             "screened with hanging hides, and a crude watchtower of "
             "lashed poles rises from the barn roof. The yard is "
             "littered with stolen goods: sacks of grain, coils of "
             "rope, a cartwheel leaning against the well. These are "
             "outlaws who can't or won't return to town."),
        ],
    )
    rooms["bandit_holdfast"].details = {
        "watchtower": (
            "Four poles lashed together with rope, supporting a "
            "platform of rough planks barely big enough for one person. "
            "It gives a clear view of the road and the surrounding "
            "fields — enough warning to prepare for trouble."
        ),
        "goods": (
            "A mix of stolen supplies and scavenged equipment. Grain "
            "sacks with the Goldwheat Farm brand, rope that looks like "
            "it came from the docks, tools lifted from the farms. "
            "Nothing valuable enough to fence — just survival supplies."
        ),
    }

    rooms["bandit_camp"] = create_object(
        RoomBase,
        key="Bandit Camp",
        attributes=[
            ("desc",
             "Behind the holdfast, a rough camp sprawls in what was "
             "once a kitchen garden. Bedrolls and lean-tos surround a "
             "central firepit where something is always cooking — "
             "rabbit stew, by the smell. A rack of weapons stands "
             "near the fire: clubs, hand axes, a few rusty short "
             "swords. The bandits here are desperate rather than "
             "organised — farmers and labourers turned outlaw by debt, "
             "bad luck, or worse choices. They watch strangers with a "
             "mix of suspicion and hope."),
        ],
    )
    rooms["bandit_camp"].details = {
        "weapons": (
            "A sad collection. Woodcutter's axes repurposed for "
            "fighting, clubs with nails driven through the heads, "
            "and short swords so pitted with rust they might snap "
            "on a hard parry. These aren't professional bandits — "
            "they're people who ran out of options."
        ),
        "camp": (
            "Lean-tos made from salvaged planks and canvas, bedrolls "
            "of patched wool blankets. A few personal items are "
            "visible — a child's carved toy, a prayer token from the "
            "temple, a woman's embroidered handkerchief. Whatever "
            "drove these people out here, they brought pieces of "
            "their old lives with them."
        ),
    }

    # ── Moonpetal Fields (7 rooms) ───────────────────────────────────

    rooms["moonpetal_approach"] = create_object(
        RoomBase,
        key="Moonpetal Approach",
        attributes=[
            ("desc",
             "The road descends into a shallow valley where the soil "
             "turns dark and rich. The air is different here — sweeter, "
             "with a faint luminous quality even in daylight. Wild "
             "flowers grow in profusion along the roadside, their "
             "petals in shades of silver and pale violet. Ahead, the "
             "valley opens into wide meadows where the moonpetal "
             "grows wild — the base ingredient for every potion the "
             "apothecary can brew."),
        ],
    )
    rooms["moonpetal_approach"].details = {
        "flowers": (
            "The wild flowers here are mostly moonpetal — delicate "
            "blooms with silvery petals that seem to glow faintly "
            "from within. They open at dusk and close at dawn, but "
            "even in daylight their luminous quality is visible. "
            "The alchemists of Millholm depend on these fields."
        ),
    }

    # 2x3 moonpetal harvest grid
    _moonpetal_attrs = [
        ("resource_id", 12),
        ("resource_count", 0),
        ("abundance_threshold", 5),
        ("harvest_height", 0),
        ("harvest_command", "gather"),
        ("desc_abundant",
         "Moonpetal grows thick and wild here, the silvery blooms "
         "carpeting the meadow in every direction. There is plenty "
         "to 'gather'."),
        ("desc_scarce",
         "Most of the moonpetal has been picked. A few pale blooms "
         "still dot the meadow, ready to 'gather'."),
        ("desc_depleted",
         "The meadow has been picked clean of moonpetal. Only bare "
         "stems and trampled grass remain. The flowers will need "
         "time to regrow."),
    ]

    _field_descs = [
        # Row 0 (south): c0=west, c1=east
        ("Moonpetal Field",
         "A wide meadow of dark soil and silver-petalled flowers. "
         "The moonpetal here grows in dense clusters, their stems "
         "tangled together and their blooms turned toward the sky. "
         "The air is thick with their sweet, faintly metallic scent. "
         "Bees drift lazily between the flowers."),
        ("Moonpetal Field",
         "The eastern edge of the moonpetal fields borders a stand "
         "of young birch trees whose white bark catches the light. "
         "Moonpetal grows right up to the treeline, the silvery "
         "blooms bright against the dark earth. A rabbit warren "
         "has been dug beneath the nearest birch."),
        # Row 1 (middle)
        ("Moonpetal Field",
         "The heart of the moonpetal meadow, where the flowers grow "
         "thickest and tallest. The blooms reach knee-height here, "
         "their silver petals so dense they create a shimmering "
         "carpet that seems to ripple in the breeze. The scent is "
         "almost overwhelming — sweet and heavy and faintly magical."),
        ("Moonpetal Field",
         "A gentle slope in the meadow where rainwater collects in "
         "a shallow depression. The moonpetal here is especially "
         "vigorous, fed by the extra moisture. Dragonflies hover "
         "over the damp patch, and the petals of the nearest flowers "
         "are beaded with dew."),
        # Row 2 (north)
        ("Moonpetal Field",
         "The northern reach of the moonpetal fields, where the "
         "flowers thin gradually into ordinary grassland. A tumbled "
         "stone wall — the remnant of an old field boundary — runs "
         "east-west, half buried in wildflowers. Beyond it, the "
         "grass grows taller and wilder."),
        ("Moonpetal Field",
         "The far corner of the meadow, where moonpetal mingles "
         "with wild thyme and chamomile. The mixed scent is "
         "pleasant but less potent than the pure moonpetal fields "
         "to the south. A scarecrow stands at a drunken angle, "
         "its straw body colonised by nesting sparrows."),
    ]

    mp_grid = []  # mp_grid[row][col], row 0=south, 2=north
    idx = 0
    for row in range(3):
        grid_row = []
        for col in range(2):
            name, desc = _field_descs[idx]
            room = create_object(
                RoomHarvesting,
                key=name,
                attributes=list(_moonpetal_attrs) + [("desc", desc)],
            )
            rooms[f"moonpetal_r{row}_c{col}"] = room
            grid_row.append(room)
            idx += 1
        mp_grid.append(grid_row)

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

    # ══════════════════════════════════════════════════════════════════
    # 2. CREATE EXITS
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # ── Countryside connections ──────────────────────────────────────
    # countryside_road ← south_gate (wired in build_game_world.py)
    # countryside_road ← south_fork_end (wired in build_game_world.py)
    connect_bidirectional_exit(rooms["countryside_road"], rooms["farmstead_fork"], "south")
    connect_bidirectional_exit(rooms["farmstead_fork"], rooms["bandit_holdfast"], "west")
    connect_bidirectional_exit(rooms["bandit_holdfast"], rooms["bandit_camp"], "west")
    exit_count += 8

    # ── Moonpetal Fields ─────────────────────────────────────────────
    # Grid flows south: approach → row 2 (north) → row 1 → row 0 (south)
    connect_bidirectional_exit(rooms["farmstead_fork"], rooms["moonpetal_approach"], "south")
    connect_bidirectional_exit(rooms["moonpetal_approach"], mp_grid[2][0], "south")
    exit_count += 4

    # Grid: horizontal connections (east-west)
    for row in range(3):
        connect_bidirectional_exit(mp_grid[row][0], mp_grid[row][1], "east")
    exit_count += 6

    # Grid: vertical connections — south flows deeper into district
    for col in range(2):
        for row in range(2):
            connect_bidirectional_exit(mp_grid[row + 1][col], mp_grid[row][col], "south")
    exit_count += 8

    # ── Gnoll Territory ──────────────────────────────────────────────
    # Path continues south: moonpetal grid → grasslands → hunting grounds
    # → gnoll camp → lookout → shadowsward
    connect_bidirectional_exit(mp_grid[0][0], rooms["wild_grasslands"], "south")
    connect_bidirectional_exit(rooms["wild_grasslands"], rooms["gnoll_hunting_grounds"], "south")
    connect_bidirectional_exit(rooms["gnoll_hunting_grounds"], rooms["ravaged_farmstead"], "west")
    connect_bidirectional_exit(rooms["gnoll_hunting_grounds"], rooms["gnoll_camp"], "south")
    connect_bidirectional_exit(rooms["gnoll_camp"], rooms["gnoll_lookout"], "south")
    exit_count += 10

    # ── Barrow (hidden entrance) ─────────────────────────────────────
    connect_bidirectional_exit(rooms["gnoll_hunting_grounds"], rooms["barrow_hill"], "east")
    exit_count += 2

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
    door_ab.find_dc = 18
    exit_count += 2

    # Barrow interior
    connect_bidirectional_exit(rooms["barrow_entrance"], rooms["bone_passage"], "south")
    connect_bidirectional_exit(rooms["bone_passage"], rooms["ancient_catacombs"], "south")
    connect_bidirectional_exit(rooms["ancient_catacombs"], rooms["necromancers_study"], "south")
    exit_count += 6

    # ── Shadowsward ────────────────────────────────────────────────────
    # Path continues south past gnoll territory
    connect_bidirectional_exit(rooms["gnoll_lookout"], rooms["southern_approach"], "south")
    connect_bidirectional_exit(rooms["southern_approach"], rooms["shadowsward_gate"], "south")
    exit_count += 4

    print(f"  Created {exit_count} exits.")

    # ══════════════════════════════════════════════════════════════════
    # 3. TAG ROOMS — zone, district, terrain
    # ══════════════════════════════════════════════════════════════════

    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # Countryside — rural terrain
    rural_keys = [
        "countryside_road", "farmstead_fork",
        "bandit_holdfast", "bandit_camp",
    ]
    for key in rural_keys:
        rooms[key].set_terrain(TerrainType.RURAL.value)

    # Moonpetal fields — plains terrain
    rooms["moonpetal_approach"].set_terrain(TerrainType.PLAINS.value)
    for row in range(3):
        for col in range(2):
            mp_grid[row][col].set_terrain(TerrainType.PLAINS.value)

    # Gnoll territory — plains terrain
    plains_keys = [
        "wild_grasslands", "gnoll_hunting_grounds",
        "ravaged_farmstead", "gnoll_camp", "gnoll_lookout",
    ]
    for key in plains_keys:
        rooms[key].set_terrain(TerrainType.PLAINS.value)

    # Barrow hill (surface) — plains
    rooms["barrow_hill"].set_terrain(TerrainType.PLAINS.value)

    # Barrow underground
    underground_keys = [
        "barrow_entrance", "bone_passage",
        "ancient_catacombs", "necromancers_study",
    ]
    for key in underground_keys:
        rooms[key].set_terrain(TerrainType.UNDERGROUND.value)

    # Shadowsward — plains terrain
    rooms["southern_approach"].set_terrain(TerrainType.PLAINS.value)
    rooms["shadowsward_gate"].set_terrain(TerrainType.PLAINS.value)

    print("  Tagged all rooms with zone, district, and terrain.")

    # ── Mob area tags ──
    gnoll_rooms = [
        "wild_grasslands", "gnoll_hunting_grounds",
        "ravaged_farmstead", "gnoll_camp", "gnoll_lookout",
    ]
    for key in gnoll_rooms:
        rooms[key].tags.add("gnoll_territory", category="mob_area")
    print(f"  Tagged {len(gnoll_rooms)} rooms with mob_area=gnoll_territory.")

    # Pin the Gnoll Warlord boss spawn to its single room via a dedicated
    # mob_area tag — separate from gnoll_territory so target=1 room
    # selection always lands in the camp.
    rooms["gnoll_camp"].tags.add("gnoll_camp_boss", category="mob_area")

    # ══════════════════════════════════════════════════════════════════
    # 4. FUTURE CONNECTION NOTES
    # ══════════════════════════════════════════════════════════════════
    # countryside_road: connects north to town_rooms["south_gate"] (wired in build_game_world.py)
    # countryside_road: connects west to farm_rooms["south_fork_end"] (wired in build_game_world.py)
    # shadowsward_gate: future zone transition (SKILLED cartography required)
    # necromancers_study: future NPC placement (necromancy trainer, non-lethal quest)
    # bandit rooms: future bandit mob spawns
    # bone_passage: future undead mob spawns (escaped experiments)

    # ── Region map cell tags ────────────────────────────────────────
    _rt = "millholm_region"

    # South road column (west branch from farm fork)
    rooms["countryside_road"].tags.add(f"{_rt}:south_road_1", category="map_cell")
    rooms["farmstead_fork"].tags.add(f"{_rt}:south_road_2", category="map_cell")

    # Bandits
    rooms["bandit_holdfast"].tags.add(f"{_rt}:bandits", category="map_cell")
    rooms["bandit_camp"].tags.add(f"{_rt}:bandits", category="map_cell")

    # Moonpetal fields
    rooms["moonpetal_approach"].tags.add(f"{_rt}:moonpetal_fields", category="map_cell")
    for row in mp_grid:
        for room in row:
            room.tags.add(f"{_rt}:moonpetal_fields", category="map_cell")

    # Gnoll territory
    rooms["wild_grasslands"].tags.add(f"{_rt}:gnoll_territory", category="map_cell")
    rooms["gnoll_hunting_grounds"].tags.add(f"{_rt}:gnoll_territory", category="map_cell")
    rooms["gnoll_camp"].tags.add(f"{_rt}:gnoll_territory", category="map_cell")
    rooms["gnoll_lookout"].tags.add(f"{_rt}:gnoll_territory", category="map_cell")

    # Ravaged farmstead
    rooms["ravaged_farmstead"].tags.add(f"{_rt}:ravaged_farmstead", category="map_cell")

    # Barrow hill (hidden — will only reveal when player finds it)
    rooms["barrow_hill"].tags.add(f"{_rt}:barrow_hill", category="map_cell")

    # Shadowsward approach and gate
    rooms["southern_approach"].tags.add(f"{_rt}:south_approach_e", category="map_cell")
    rooms["shadowsward_gate"].tags.add(f"{_rt}:shadowsward_gate", category="map_cell")

    print(f"  Tagged southern rooms with {_rt} map_cell tags.")

    print("  Millholm Southern District complete.\n")
    return rooms

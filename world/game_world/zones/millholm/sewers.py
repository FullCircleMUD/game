"""
Millholm Sewers — the underground district beneath Millholm Town.

Builds ~26 rooms including:
- Sewer proper (18 rooms): a winding drain system with 5 dead ends
  - Main spine: Blocked Grate, Rat Nest, Collapsed Section
  - Cistern branch: Submerged Alcove, Bricked-Up Passage
- Thieves' Lair (8 rooms): hidden guild hideout beneath the sewers
  - Guard Post, Thieves' Hall, Barracks, Planning Room,
    Stolen Goods Stash, Shadow Mistress's Chamber

Cross-district hidden doors (cellar→sewer entrance, abandoned house→old cistern)
are created in build_game_world.py after both districts are built.

Usage:
    from world.game_world.millholm_sewers import build_millholm_sewers
    build_millholm_sewers()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from utils.exit_helpers import (
    connect_bidirectional_exit,
    connect_bidirectional_door_exit,
    connect_bidirectional_trapped_door_exit,
    connect_bidirectional_tripwire_exit,
)


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_sewers"


def _tag_room(room, terrain):
    """Apply standard zone/district/terrain tags to a sewer room."""
    room.tags.add(ZONE, category="zone")
    room.tags.add(DISTRICT, category="district")
    room.set_terrain(terrain)


def build_millholm_sewers():
    """Build the Millholm Sewers district and return a dict of key rooms."""
    rooms = {}

    # ====================================================================
    #  SEWER PROPER  (12 rooms, terrain UNDERGROUND)
    # ====================================================================
    T = TerrainType.UNDERGROUND.value

    rooms["sewer_entrance"] = create_object(
        RoomBase,
        key="Sewer Entrance",
        attributes=[(
            "desc",
            "A narrow passage opens into a low-ceilinged tunnel of crumbling "
            "brickwork. Water trickles along a shallow channel cut into the "
            "floor, carrying the unmistakable stench of the town above. "
            "Patches of luminescent moss cling to the walls, casting a faint "
            "sickly glow over the damp stonework. The tunnel descends steeply "
            "into darkness below.",
        )],
    )
    _tag_room(rooms["sewer_entrance"], T)

    rooms["main_drain"] = create_object(
        RoomBase,
        key="Main Drain",
        attributes=[(
            "desc",
            "The tunnel widens into a proper drain channel, broad enough for "
            "two people to walk abreast. Ankle-deep water flows sluggishly "
            "south through a central gutter. The brick walls are streaked with "
            "mineral deposits and dark stains. Rusty iron brackets, once "
            "holding torches, jut from the walls at regular intervals.",
        )],
    )
    _tag_room(rooms["main_drain"], T)

    rooms["drain_junction"] = create_object(
        RoomBase,
        key="Drain Junction",
        attributes=[(
            "desc",
            "Three drain channels converge here in a wide circular chamber. "
            "An iron grate set into the ceiling allows a thin shaft of "
            "daylight to filter down, illuminating the swirling water below. "
            "The main channel continues south, while a narrower pipe branches "
            "east. Scratching sounds echo from somewhere in the walls.",
        )],
    )
    _tag_room(rooms["drain_junction"], T)

    rooms["eastern_pipe"] = create_object(
        RoomBase,
        key="Eastern Pipe",
        attributes=[(
            "desc",
            "This narrow pipe forces you to crouch as you wade through "
            "knee-deep murky water. The walls are slick with algae and the "
            "air is thick with moisture. Ahead, a faint glimmer of light "
            "suggests an opening to the east.",
        )],
    )
    _tag_room(rooms["eastern_pipe"], T)

    rooms["blocked_grate"] = create_object(
        RoomBase,
        key="Blocked Grate",
        attributes=[(
            "desc",
            "The pipe ends at a heavy iron grate set into the outer wall. "
            "Through the rusted bars you can see a drainage ditch outside, "
            "with daylight and fresh air tantalisingly close. The grate is "
            "welded shut with years of corrosion — there's no getting "
            "through. You'll have to go back the way you came.",
        )],
    )
    _tag_room(rooms["blocked_grate"], T)

    rooms["flooded_tunnel"] = create_object(
        RoomBase,
        key="Flooded Tunnel",
        attributes=[(
            "desc",
            "The water level rises sharply here, reaching waist height in "
            "places. The current is stronger, fed by unseen tributaries in "
            "the walls. Something splashes in the darkness ahead. The tunnel "
            "continues south, though a side passage branches west into an "
            "even darker recess.",
        )],
    )
    _tag_room(rooms["flooded_tunnel"], T)

    rooms["rat_nest"] = create_object(
        RoomBase,
        key="Rat Nest",
        attributes=[(
            "desc",
            "The side tunnel dead-ends in a fetid alcove piled with refuse "
            "and gnawed bones. Dozens of pairs of tiny red eyes gleam in "
            "the darkness as rats scurry across every surface. The stench "
            "is overwhelming — rotting food, animal waste, and something "
            "worse. There's nothing of value here, and the rats are growing "
            "agitated at your presence.",
        )],
    )
    _tag_room(rooms["rat_nest"], T)

    rooms["deep_sewer"] = create_object(
        RoomBase,
        key="Deep Sewer",
        attributes=[(
            "desc",
            "The architecture here is older, the brickwork replaced by "
            "rough-hewn stone blocks fitted together without mortar. This "
            "section predates the town above by centuries. The ceiling is "
            "higher, vaulted in a style that suggests this was once something "
            "other than a sewer. Water drips steadily from above, and the "
            "air is cold and still. A passage leads east, partially blocked "
            "by rubble.",
        )],
    )
    _tag_room(rooms["deep_sewer"], T)

    rooms["collapsed_section"] = create_object(
        RoomBase,
        key="Collapsed Section",
        attributes=[(
            "desc",
            "A catastrophic cave-in has brought tonnes of earth and stone "
            "crashing down, completely blocking the passage ahead. Broken "
            "timber supports jut from the debris at odd angles. A trickle "
            "of dust still falls from the unstable ceiling above. Whatever "
            "lies beyond is thoroughly inaccessible — digging through would "
            "risk bringing the whole tunnel down.",
        )],
    )
    _tag_room(rooms["collapsed_section"], T)

    rooms["overflow_chamber"] = create_object(
        RoomBase,
        key="Overflow Chamber",
        attributes=[(
            "desc",
            "A large vaulted chamber serves as a catchment for excess water "
            "during heavy rains. High-water marks on the walls show it can "
            "fill nearly to the ceiling. Currently the water is only ankle-"
            "deep, pooling in the centre before draining through cracks in "
            "the floor. Passages lead in several directions, and the tunnel "
            "continues south.",
        )],
    )
    _tag_room(rooms["overflow_chamber"], T)

    rooms["old_cistern"] = create_object(
        RoomBase,
        key="Old Cistern",
        attributes=[(
            "desc",
            "A cylindrical chamber lined with ancient glazed tiles, many "
            "cracked or missing. This cistern once supplied fresh water to "
            "the buildings above, but it has long been abandoned. A rusted "
            "ladder climbs the north wall, ending at a sealed hatch far "
            "overhead. The water here is clearer than elsewhere in the "
            "sewers, fed by a natural spring that seeps through the "
            "eastern wall.",
        )],
    )
    _tag_room(rooms["old_cistern"], T)

    # ── Cistern branch (Old Cistern → Overflow Chamber via 4 rooms) ──
    rooms["waterlogged_passage"] = create_object(
        RoomBase,
        key="Waterlogged Passage",
        attributes=[(
            "desc",
            "South of the cistern, the passage drops sharply and the water "
            "rises to knee height. The walls are coated in a thick layer of "
            "grey-green slime that glistens in the dim light. Every step "
            "produces a sucking sound as your feet pull free of the silty "
            "bottom. The air is heavy and stale, tasting of minerals and "
            "decay. The passage continues south into deeper water.",
        )],
    )
    _tag_room(rooms["waterlogged_passage"], T)

    from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting

    rooms["fungal_grotto"] = create_object(
        RoomHarvesting,
        key="Fungal Grotto",
        attributes=[
            ("desc",
             "The tunnel opens into a natural cavern where the brickwork has "
             "given way entirely to raw stone. Enormous fungi — some taller "
             "than a person — grow in clusters from the damp floor and walls, "
             "their caps glowing with a faint blue-green bioluminescence. "
             "Spores drift lazily through the air like underwater snow. Among "
             "the larger specimens, fat bulbous mushrooms with mottled grey "
             "caps cluster in the damp crevices. A narrow gap leads east, "
             "partially submerged, while the main passage continues south."),
            ("resource_id", 17),           # Ogre's Cap
            ("resource_count", 0),         # spawn script sets amount
            ("abundance_threshold", 5),
            ("harvest_height", 0),
            ("harvest_command", "gather"),
            ("desc_abundant",
             "Fat, bulbous mushrooms with mottled grey caps crowd the damp "
             "grotto floor. There are plenty of ogre's caps to gather."),
            ("desc_scarce",
             "A few pale ogre's caps cling to the crevices, their caps thin "
             "and small. The supply is running low."),
            ("desc_depleted",
             "The crevices are bare — the ogre's caps have all been picked. "
             "Only the enormous bioluminescent fungi remain, useless for "
             "alchemy."),
            ("always_lit", True),  # bioluminescence
        ],
    )
    _tag_room(rooms["fungal_grotto"], T)

    rooms["submerged_alcove"] = create_object(
        RoomBase,
        key="Submerged Alcove",
        attributes=[(
            "desc",
            "The narrow gap opens into a small flooded chamber where the "
            "water reaches chest height. The remains of old wooden shelving "
            "jut from the walls, whatever they once held long since rotted "
            "away or washed downstream. Something metallic glints beneath "
            "the murky water, but the depth makes it impossible to "
            "investigate further. There's nowhere to go but back.",
        )],
    )
    _tag_room(rooms["submerged_alcove"], T)

    rooms["narrow_crawlway"] = create_object(
        RoomBase,
        key="Narrow Crawlway",
        attributes=[(
            "desc",
            "The passage narrows dramatically, forcing you to turn sideways "
            "to squeeze through. The ceiling drops so low you must duck, "
            "and the rough stone scrapes against your back and chest. Cobwebs "
            "brush your face in the darkness. After what feels like an "
            "eternity of claustrophobic shuffling, the tunnel widens again "
            "to the south.",
        )],
    )
    _tag_room(rooms["narrow_crawlway"], T)

    rooms["ancient_drain"] = create_object(
        RoomBase,
        key="Ancient Drain",
        attributes=[(
            "desc",
            "This section of tunnel is far older than anything above. The "
            "walls are carved from the bedrock itself, with chisel marks "
            "still visible despite centuries of water erosion. Strange "
            "symbols are etched into the stone at regular intervals — too "
            "weathered to read but clearly deliberate. A bricked-up passage "
            "is visible to the west, while a wider tunnel leads east.",
        )],
    )
    _tag_room(rooms["ancient_drain"], T)

    rooms["bricked_up_passage"] = create_object(
        RoomBase,
        key="Bricked-Up Passage",
        attributes=[(
            "desc",
            "Someone has carefully bricked up this passage with newer "
            "masonry, distinctly different from the ancient stonework "
            "surrounding it. Mortar still clings stubbornly between the "
            "bricks despite the damp. Through a small crack near the top, "
            "a faint current of dry air flows — there's definitely space "
            "beyond, but the wall is solid and would take serious tools to "
            "breach. A dead end for now.",
        )],
    )
    _tag_room(rooms["bricked_up_passage"], T)

    rooms["crumbling_wall"] = create_object(
        RoomBase,
        key="Crumbling Wall",
        attributes=[(
            "desc",
            "The tunnel ends at a wall of ancient masonry, different in "
            "style from the sewer brickwork. Several stones have crumbled "
            "away, revealing dark gaps between them. A faint draught pushes "
            "through the cracks, carrying a scent of lamp oil and something "
            "else — leather, perhaps, or sweat. The wall looks structurally "
            "unsound, as though it might conceal a passage beyond.",
        )],
    )
    _tag_room(rooms["crumbling_wall"], T)

    # ====================================================================
    #  THIEVES' LAIR  (8 rooms, terrain DUNGEON)
    # ====================================================================
    D = TerrainType.DUNGEON.value

    rooms["thieves_tunnel"] = create_object(
        RoomBase,
        key="Thieves' Tunnel",
        attributes=[(
            "desc",
            "Beyond the crumbling wall, the rough sewer stonework gives way "
            "to a properly maintained passage. The floor has been swept, the "
            "walls reinforced with fresh timbers, and oil lamps hang at "
            "intervals, filling the tunnel with warm flickering light. "
            "Someone is clearly keeping this place in good repair. The "
            "passage leads south, deeper into whatever lies beyond.",
        )],
    )
    _tag_room(rooms["thieves_tunnel"], D)

    rooms["guard_post"] = create_object(
        RoomBase,
        key="Guard Post",
        attributes=[(
            "desc",
            "A small fortified alcove has been carved out of the tunnel wall, "
            "with a wooden bench, a weapon rack holding a crossbow and short "
            "sword, and a battered table with a half-eaten meal. Arrow slits "
            "have been cut into a low stone wall facing north, giving a clear "
            "line of fire down the approach tunnel. Whoever maintains this "
            "post takes security seriously.",
        )],
    )
    _tag_room(rooms["guard_post"], D)

    rooms["thieves_hall"] = create_object(
        RoomBase,
        key="Thieves' Hall",
        attributes=[(
            "desc",
            "A surprisingly spacious underground hall, well-lit by dozens of "
            "oil lamps and a few stolen candelabras. Rough wooden tables and "
            "benches fill the centre, while tapestries — clearly pilfered "
            "from wealthy homes — cover the stone walls. A large map of "
            "Millholm is pinned to a board near the east exit, covered in "
            "markings and notations. This is clearly the common room of an "
            "organised group.",
        )],
    )
    _tag_room(rooms["thieves_hall"], D)

    rooms["planning_room"] = create_object(
        RoomBase,
        key="Planning Room",
        attributes=[(
            "desc",
            "A private chamber fitted out as a war room for thieves. A large "
            "table dominates the centre, covered with detailed building plans, "
            "guard patrol schedules, and notes on the movements of wealthy "
            "merchants. Charcoal sketches of lock mechanisms and safe designs "
            "are pinned to every wall. A locked chest sits in the corner — "
            "presumably containing the guild's most sensitive documents.",
        )],
    )
    _tag_room(rooms["planning_room"], D)

    rooms["barracks"] = create_object(
        RoomBase,
        key="Barracks",
        attributes=[(
            "desc",
            "Rows of simple wooden bunks line the walls of this long, narrow "
            "room. Each bunk has a thin straw mattress and a small locked "
            "chest at its foot for personal belongings. A few cloaks and dark "
            "clothing hang from pegs between the beds. The room smells of "
            "boot leather and cheap wine. Despite the cramped quarters, "
            "everything is reasonably tidy — discipline is maintained here.",
        )],
    )
    _tag_room(rooms["barracks"], D)

    rooms["stolen_goods"] = create_object(
        RoomBase,
        key="Stolen Goods Stash",
        attributes=[(
            "desc",
            "Crates, barrels, and sacks are piled high in this cluttered "
            "storeroom, each marked with cryptic chalk symbols denoting their "
            "contents and origin. Bolts of fine silk lean against one wall "
            "next to stacked silverware and a rack of quality weapons. A "
            "ledger on a small desk records every item — the guild keeps "
            "meticulous accounts of its ill-gotten gains.",
        )],
    )
    _tag_room(rooms["stolen_goods"], D)

    rooms["shadow_mistress_chamber"] = create_object(
        RoomBase,
        key="Shadow Mistress's Chamber",
        attributes=[(
            "desc",
            "The guild leader's private quarters are surprisingly refined. "
            "A four-poster bed draped in dark velvet occupies one corner, "
            "while an ornate desk holds neat stacks of correspondence sealed "
            "with unmarked wax. A weapons rack displays an impressive "
            "collection of daggers and a single exquisite rapier. A large "
            "mirror on one wall seems oddly placed — perhaps it conceals "
            "something. The room speaks of someone cultured, dangerous, and "
            "very much in control.",
        )],
    )
    _tag_room(rooms["shadow_mistress_chamber"], D)

    rooms["training_alcove"] = create_object(
        RoomBase,
        key="Training Alcove",
        attributes=[(
            "desc",
            "A section of the lair has been set aside for practice. Straw "
            "dummies bristle with throwing knives, and a series of wooden "
            "posts are rigged with bells and tripwires for stealth training. "
            "A lockpicking practice board mounted on the wall holds a dozen "
            "locks of increasing complexity. Chalk marks on the floor outline "
            "various combat stances and footwork patterns.",
        )],
    )
    _tag_room(rooms["training_alcove"], D)

    # ── Thieves' Gauntlet (3 rooms off Training Alcove) ──────────────

    rooms["gauntlet_corridor"] = create_object(
        RoomBase,
        key="Narrow Corridor",
        attributes=[
            ("desc",
             "A cramped stone corridor, barely wide enough for one person. "
             "The walls are damp and the air smells of old rust. Cobwebs "
             "hang in thick curtains from the low ceiling, but someone has "
             "cleared a path through them recently — the broken strands "
             "are still sticky. Ahead, an iron door is set into the wall. "
             "Something about the door frame doesn't look right — the "
             "mortar around the hinges is a slightly different colour "
             "from the rest, as if it's been modified. On the opposite "
             "wall, one brick sits slightly askew, its edges worn smoother "
             "than its neighbours."),
            ("details", {
                "frame": (
                    "The door frame has been altered. The mortar around "
                    "the upper hinge is newer than the surrounding stone, "
                    "and tiny holes are drilled into the lintel. Something "
                    "is hidden inside the frame."
                ),
                "cobwebs": (
                    "Thick cobwebs, mostly cleared. The path through them "
                    "is recent — someone comes this way regularly."
                ),
                "brick": (
                    "One brick on the opposite wall sits slightly askew. "
                    "The edges are worn smoother than its neighbours, as "
                    "if many hands have pressed it over the years."
                ),
            }),
        ],
    )
    _tag_room(rooms["gauntlet_corridor"], D)

    rooms["gauntlet_lever_room"] = create_object(
        RoomBase,
        key="Damp Chamber",
        attributes=[
            ("desc",
             "A low-ceilinged chamber where water seeps through the "
             "stone, leaving the floor slick and treacherous. The air is "
             "cold and still. The passage continues west through a narrow "
             "archway. A thin wire glints in the torchlight just above "
             "ankle height near the archway — carelessly placed, or "
             "deliberately obvious? The south wall is rougher than the "
             "others, the stones uneven and poorly mortared. One stone "
             "in particular juts out slightly further than its neighbours, "
             "as if it were meant to be pushed."),
            ("details", {
                "wire": (
                    "A thin wire stretched across the passage at ankle "
                    "height, just before the archway. It's attached to "
                    "something in the wall on both sides. Stepping on it "
                    "would be bad."
                ),
                "stone": (
                    "One stone in the south wall protrudes slightly. The "
                    "edges are worn smooth, as if it has been pushed many "
                    "times before. It looks like it moves."
                ),
                "wall": (
                    "The south wall is rougher than the others. One stone "
                    "juts out — worn smooth on the edges. It has been "
                    "pushed before. Many times."
                ),
            }),
        ],
    )
    _tag_room(rooms["gauntlet_lever_room"], D)

    rooms["gauntlet_vault"] = create_object(
        RoomBase,
        key="The Vault",
        attributes=[
            ("desc",
             "A small, dry chamber at the end of the gauntlet. A heavy "
             "iron chest sits against the far wall, secured with a "
             "padlock. The walls are bare stone — no decoration, no "
             "furniture, just the chest and the faint sound of dripping "
             "water from somewhere above. The floor is dusty, but the "
             "dust around the base of the chest has been disturbed. "
             "Scratch marks in the dust lead from the chest to the east "
             "wall and back, as if something has been dragged across "
             "the floor. The east wall has a loose stone near the base, "
             "just above floor level — easy to miss if you weren't "
             "looking for it."),
            ("details", {
                "chest": (
                    "A heavy iron chest with a brass padlock. The chest "
                    "itself is bolted to the floor. Whatever is inside "
                    "is meant to be earned, not carried away."
                ),
                "scratch marks": (
                    "Scratches in the dust, leading from the chest to "
                    "the east wall and back. Something small has been "
                    "dragged back and forth — or hidden and retrieved."
                ),
                "stone": (
                    "A loose stone near the base of the east wall, just "
                    "above floor level. The mortar around it has crumbled "
                    "away. It looks like it could be pulled free."
                ),
                "wall": (
                    "The east wall is plain stone, but near the floor "
                    "there's a loose stone with crumbled mortar. Something "
                    "might be hidden behind it."
                ),
            }),
        ],
    )
    _tag_room(rooms["gauntlet_vault"], D)

    # ====================================================================
    #  EXITS — Sewer Proper
    # ====================================================================

    # Main sewer spine (north to south)
    connect_bidirectional_exit(rooms["sewer_entrance"], rooms["main_drain"], "down")
    connect_bidirectional_exit(rooms["main_drain"], rooms["drain_junction"], "south")
    connect_bidirectional_exit(rooms["drain_junction"], rooms["flooded_tunnel"], "south")
    connect_bidirectional_exit(rooms["flooded_tunnel"], rooms["deep_sewer"], "south")
    connect_bidirectional_exit(rooms["deep_sewer"], rooms["overflow_chamber"], "south")
    connect_bidirectional_exit(rooms["overflow_chamber"], rooms["crumbling_wall"], "south")

    # Dead-end branches
    connect_bidirectional_exit(rooms["drain_junction"], rooms["eastern_pipe"], "east")
    connect_bidirectional_exit(rooms["eastern_pipe"], rooms["blocked_grate"], "east")
    connect_bidirectional_exit(rooms["flooded_tunnel"], rooms["rat_nest"], "west")
    connect_bidirectional_exit(rooms["deep_sewer"], rooms["collapsed_section"], "east")

    # Cistern branch (Old Cistern → Overflow Chamber via 4 rooms + 2 dead ends)
    connect_bidirectional_exit(rooms["old_cistern"], rooms["waterlogged_passage"], "south")
    connect_bidirectional_exit(rooms["waterlogged_passage"], rooms["fungal_grotto"], "south")
    connect_bidirectional_exit(rooms["fungal_grotto"], rooms["submerged_alcove"], "east")
    connect_bidirectional_exit(rooms["fungal_grotto"], rooms["narrow_crawlway"], "south")
    connect_bidirectional_exit(rooms["narrow_crawlway"], rooms["ancient_drain"], "south")
    connect_bidirectional_exit(rooms["ancient_drain"], rooms["bricked_up_passage"], "west")
    connect_bidirectional_exit(rooms["ancient_drain"], rooms["overflow_chamber"], "east")

    # ====================================================================
    #  EXIT — Hidden door: Crumbling Wall → Thieves' Tunnel (find_dc=20)
    # ====================================================================

    door_ab, door_ba = connect_bidirectional_door_exit(
        rooms["crumbling_wall"], rooms["thieves_tunnel"], "south",
        key="a section of loose masonry",
        closed_ab=(
            "The south wall is made of ancient crumbling masonry. Several "
            "stones look loose enough to shift."
        ),
        open_ab=(
            "A section of the south wall has been pushed aside, revealing "
            "a well-maintained passage beyond."
        ),
        closed_ba=(
            "A wall of rough masonry blocks the passage north. It looks "
            "like it can be pushed back into place."
        ),
        open_ba=(
            "The concealed wall stands open, the damp sewers visible beyond."
        ),
        door_name="wall",
    )
    door_ab.is_hidden = True
    door_ab.find_dc = 12

    # ====================================================================
    #  EXITS — Thieves' Lair
    # ====================================================================

    connect_bidirectional_exit(rooms["thieves_tunnel"], rooms["guard_post"], "south")
    connect_bidirectional_exit(rooms["guard_post"], rooms["thieves_hall"], "south")
    connect_bidirectional_exit(rooms["thieves_hall"], rooms["planning_room"], "east")
    connect_bidirectional_exit(rooms["thieves_hall"], rooms["barracks"], "west")
    connect_bidirectional_exit(rooms["thieves_hall"], rooms["stolen_goods"], "south")
    connect_bidirectional_exit(rooms["stolen_goods"], rooms["shadow_mistress_chamber"], "east")
    connect_bidirectional_exit(rooms["guard_post"], rooms["training_alcove"], "east")

    # ── Thieves' Gauntlet exits + fixtures ───────────────────────────────

    # Hidden entrance from Training Alcove (dc 5)
    door_gauntlet, _ = connect_bidirectional_door_exit(
        rooms["training_alcove"], rooms["gauntlet_corridor"], "south",
        key="a concealed panel",
        closed_ab=(
            "The south wall looks like solid stone, but the mortar "
            "around one section is slightly different."
        ),
        open_ab=(
            "A section of the south wall has swung inward, revealing "
            "a narrow corridor beyond."
        ),
        closed_ba="A stone panel blocks the passage north.",
        open_ba="The training alcove is visible through the open panel.",
        door_name="panel",
    )
    door_gauntlet.is_hidden = True
    door_gauntlet.find_dc = 5

    # Trapped door from corridor to lever room (darts, dc 6)
    connect_bidirectional_trapped_door_exit(
        rooms["gauntlet_corridor"], rooms["gauntlet_lever_room"], "west",
        key="an iron door",
        closed_ab=(
            "A heavy iron door blocks the passage west. Something "
            "about the frame doesn't look right."
        ),
        open_ab="The iron door stands open. A damp chamber lies beyond.",
        closed_ba="An iron door leads east back to the corridor.",
        open_ba="The corridor is visible through the open door.",
        door_name="iron door",
        trap_find_dc=6,
        trap_disarm_dc=6,
        trap_damage_dice="1d2",
        trap_damage_type="piercing",
        trap_description="tiny dart holes drilled into the door frame",
        trap_one_shot=True,
        trap_side="ab",
    )

    # Tripwire from lever room to vault (bidirectional, trap on A→B side only)
    connect_bidirectional_tripwire_exit(
        rooms["gauntlet_lever_room"], rooms["gauntlet_vault"], "west",
        trap_find_dc=6,
        trap_disarm_dc=6,
        trap_damage_dice="1d2",
        trap_damage_type="piercing",
        trap_description="a thin wire stretched across the archway",
        trap_one_shot=True,
    )

    # Hidden lever in corridor — disarms the dart trap on the iron door
    from typeclasses.world_objects.gauntlet_fixtures import (
        GauntletTrapLever, DeadSwitch,
    )

    corridor_lever = create_object(
        GauntletTrapLever,
        key="a worn brick",
        location=rooms["gauntlet_corridor"],
        nohome=True,
    )
    corridor_lever.switch_verb = "push"
    corridor_lever.switch_name = "brick"
    corridor_lever.activate_msg = "You press the worn brick. It sinks into the wall with a soft click."
    corridor_lever.can_deactivate = False
    corridor_lever.is_hidden = True
    corridor_lever.find_dc = 5
    corridor_lever.db.desc = (
        "A brick that sits slightly askew in the wall. The edges are "
        "worn smoother than its neighbours, as if many hands have "
        "pressed it over the years."
    )
    corridor_lever.db.lever_activate_self_msg = (
        "You press the brick and hear a soft grinding from inside the "
        "door frame, followed by the muffled clatter of darts dropping "
        "into their housing."
    )
    corridor_lever.db.lever_activate_room_msg = (
        "presses a brick in the wall. There is a soft grinding from "
        "inside the door frame, followed by the muffled clatter of "
        "something mechanical resetting."
    )

    # Hidden lever in lever room — disarms the tripwire

    lever = create_object(
        GauntletTrapLever,
        key="a protruding stone",
        location=rooms["gauntlet_lever_room"],
        nohome=True,
    )
    lever.switch_verb = "push"
    lever.switch_name = "stone"
    lever.activate_msg = "You push the protruding stone. It sinks into the wall with a grinding sound."
    lever.can_deactivate = False
    lever.is_hidden = True
    lever.find_dc = 5
    lever.db.desc = (
        "A stone that protrudes slightly from the south wall. The "
        "edges are worn smooth from repeated use. It looks like it "
        "can be pushed."
    )
    lever.db.lever_activate_self_msg = (
        "You push the stone and hear a loud click from the passage "
        "ahead, followed by the faint twang of a wire going slack."
    )
    lever.db.lever_activate_room_msg = (
        "pushes a stone in the wall. There is a loud click from the "
        "passage ahead, followed by the faint twang of a wire going "
        "slack."
    )

    # Red herring stone in the vault — players will try to push it
    # after the previous room's stone mechanism

    dead_stone = create_object(
        DeadSwitch,
        key="a loose stone",
        location=rooms["gauntlet_vault"],
        nohome=True,
    )
    dead_stone.switch_verb = "push"
    dead_stone.switch_name = "stone"
    dead_stone.activate_msg = "You push the loose stone..."
    dead_stone.can_deactivate = False
    dead_stone.db.desc = (
        "A loose stone near the base of the east wall, just above "
        "floor level. The mortar around it has crumbled away. It "
        "looks like it could be pulled free — but pushing it does "
        "nothing useful."
    )
    dead_stone.db.dead_switch_msg = (
        "The stone shifts slightly under your hand but nothing "
        "happens. No click, no mechanism — it's just a loose "
        "stone. Perhaps the answer here lies elsewhere."
    )

    # Hidden key in the vault
    from typeclasses.world_objects.key_item import KeyItem

    vault_key = create_object(
        KeyItem,
        key="a tarnished brass key",
        location=rooms["gauntlet_vault"],
        nohome=True,
    )
    vault_key.db.desc = (
        "A small brass key, tarnished with age. It was hidden behind "
        "a loose stone in the wall."
    )
    vault_key.is_hidden = True
    vault_key.find_dc = 6
    vault_key.key_tag = "gauntlet_key"

    # Locked chest with guild token
    from typeclasses.world_objects.chest import WorldChest

    vault_chest = create_object(
        WorldChest,
        key="a heavy iron chest",
        location=rooms["gauntlet_vault"],
        nohome=True,
    )
    vault_chest.db.desc = (
        "A heavy iron chest bolted to the floor, secured with a "
        "brass padlock. Whatever is inside has been placed here "
        "deliberately — a test, not a treasure."
    )
    vault_chest.is_locked = True
    vault_chest.lock_dc = 20  # too hard to pick without skills — use the key
    vault_chest.key_tag = "gauntlet_key"

    # Guild token inside the chest
    from typeclasses.world_objects.base_world_item import WorldItem

    guild_token = create_object(
        WorldItem,
        key="a shadow guild token",
        home=rooms["gauntlet_vault"],
    )
    guild_token.db.desc = (
        "A small disc of blackened iron stamped with the Thieves' "
        "Guild mark — a dagger crossed with a key. This is proof "
        "of completing the gauntlet. Return it to Gareth Stonefield."
    )
    guild_token.move_to(vault_chest, quiet=True)

    # ── Combat flags ─────────────────────────────────────────────────────
    # Thieves' Guild rooms — safe zones for guild NPCs and training.
    no_combat_rooms = [
        rooms["thieves_hall"],
        rooms["shadow_mistress_chamber"],
        rooms["training_alcove"],
        rooms["barracks"],
    ]
    for room in no_combat_rooms:
        room.allow_combat = False
    print("  Disabled combat in Thieves' Guild rooms.")

    # ── Mob area tags (sewer proper only, NOT thieves' lair) ────────────
    sewer_mob_keys = [
        "sewer_entrance", "main_drain", "drain_junction", "eastern_pipe",
        "blocked_grate", "flooded_tunnel", "rat_nest", "deep_sewer",
        "collapsed_section", "overflow_chamber", "old_cistern",
        "waterlogged_passage", "fungal_grotto", "submerged_alcove",
        "narrow_crawlway", "ancient_drain", "bricked_up_passage",
        "crumbling_wall",
    ]
    for key in sewer_mob_keys:
        rooms[key].tags.add("sewer_rats", category="mob_area")
    print(f"  Tagged {len(sewer_mob_keys)} rooms with mob_area=sewer_rats.")

    # ── District map cell tags ────────────────────────────────────────
    # Tag sewer rooms for the millholm_sewers district map.
    # Note: bricked_up_passage room → "bricked_passage" point_key in the map stub.
    _sewer_map_tags = {
        "sewer_entrance":      "millholm_sewers:sewer_entrance",
        "main_drain":          "millholm_sewers:main_drain",
        "drain_junction":      "millholm_sewers:drain_junction",
        "eastern_pipe":        "millholm_sewers:eastern_pipe",
        "flooded_tunnel":      "millholm_sewers:flooded_tunnel",
        "deep_sewer":          "millholm_sewers:deep_sewer",
        "overflow_chamber":    "millholm_sewers:overflow_chamber",
        "crumbling_wall":      "millholm_sewers:crumbling_wall",
        "blocked_grate":       "millholm_sewers:blocked_grate",
        "rat_nest":            "millholm_sewers:rat_nest",
        "collapsed_section":   "millholm_sewers:collapsed_section",
        "old_cistern":         "millholm_sewers:old_cistern",
        "waterlogged_passage": "millholm_sewers:waterlogged_passage",
        "fungal_grotto":       "millholm_sewers:fungal_grotto",
        "narrow_crawlway":     "millholm_sewers:narrow_crawlway",
        "ancient_drain":       "millholm_sewers:ancient_drain",
        "submerged_alcove":    "millholm_sewers:submerged_alcove",
        "bricked_up_passage":  "millholm_sewers:bricked_passage",
    }
    for room_key, tag in _sewer_map_tags.items():
        rooms[room_key].tags.add(tag, category="map_cell")
    # sewer_entrance is also the region-level sewers marker
    rooms["sewer_entrance"].tags.add("millholm_region:millholm_sewers", category="map_cell")
    print(f"  Tagged {len(_sewer_map_tags)} sewer rooms with map_cell tags.")

    # ── Room count summary ─────────────────────────────────────────────
    print(f"  Millholm Sewers complete — {len(rooms)} rooms.\n")
    return rooms

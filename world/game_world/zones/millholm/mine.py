"""
Millholm Abandoned Mine — a static mine district reached via the Deep Woods.

Builds ~17 rooms:
- Surface (3 rooms): Miners' Camp (hub), Windroot Hollow (harvest), Mine Entrance
- Upper Mine / Copper Level (5 rooms): Entry Shaft, Copper Drift, Copper Seam,
  Timbered Corridor, Ore Cart Track
- Kobold Territory (3 rooms): Kobold Lookout, Flooded Gallery, Descent Shaft
- Lower Mine / Tin Level (4 rooms): Lower Junction, Tin Seam, Tin Vein,
  Kobold Warren
- Deep Mine / Mystery (2 rooms): Ancient Passage, Sealed Door

Resources: Windroot (15) on surface, Copper Ore (23) upper mine, Tin Ore (25)
lower mine. All harvest rooms start at resource_count=0 — the spawn script
sets actual amounts based on economy and demand.

Connection points:
- miners_camp: arrival from Deep Woods procedural passage (west)
- sealed_door: future content hook (deeper underground / pre-human ruins)

Usage:
    from world.game_world.millholm_mine import build_millholm_mine
    build_millholm_mine()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_harvesting import RoomHarvesting
from utils.exit_helpers import connect


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_mine"


def build_millholm_mine():
    """
    Build the Abandoned Mine district.

    Returns:
        dict of room key → room object. Key rooms for cross-district
        connections: 'miners_camp' (arrival from deep woods).
    """
    rooms = {}

    # ══════════════════════════════════════════════════════════════════
    # 1. CREATE ROOMS
    # ══════════════════════════════════════════════════════════════════

    # ── Surface (3 rooms) ─────────────────────────────────────────────

    rooms["miners_camp"] = create_object(
        RoomBase,
        key="Abandoned Miners' Camp",
        attributes=[
            ("desc",
             "A small clearing at the foot of a rocky hillside, littered "
             "with the remnants of a mining operation. Sagging canvas tents "
             "rot on their poles, and a stone-ringed firepit holds nothing "
             "but cold ash and rain. Rusted pickaxes and broken shovels lean "
             "against a stack of empty crates. The forest has begun to "
             "reclaim the camp — saplings push through the packed earth and "
             "ivy crawls over the abandoned equipment. A dark mine entrance "
             "yawns in the hillside to the east, its timbers cracked and "
             "leaning."),
        ],
    )
    rooms["miners_camp"].details = {
        "tents": (
            "Three canvas tents sag on rotting poles. The fabric is stiff "
            "with mildew and torn in places, revealing collapsed cots and "
            "scattered personal effects inside — a tin cup, a mouldering "
            "boot, a faded letter too water-damaged to read."
        ),
        "firepit": (
            "The firepit is a rough circle of soot-blackened stones. Cold "
            "ash fills the center, undisturbed for what might be months or "
            "years. Someone left a dented cooking pot balanced on the rim."
        ),
        "crates": (
            "Wooden crates, once used for hauling ore, are stacked in a "
            "tumbledown pile. Most are empty, their lids pried off. One "
            "still holds a few handfuls of worthless slag."
        ),
    }

    rooms["windroot_hollow"] = create_object(
        RoomHarvesting,
        key="Windroot Hollow",
        attributes=[
            ("desc",
             "A sheltered depression east of the camp where the hillside "
             "curves to block the wind. Pale, fibrous roots push up through "
             "the loose soil here, their thin tendrils swaying in a breeze "
             "that seems to come from the roots themselves rather than the "
             "air. The scent of open sky and distant rain rises from the "
             "earth."),
            ("resource_id", 15),
            ("resource_count", 0),
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "gather"),
            ("desc_abundant",
             "Gnarled windroot grows wild in this sheltered hollow, its "
             "pale tendrils dancing in unseen breezes. There is plenty "
             "to 'gather'."),
            ("desc_scarce",
             "Most of the windroot has been uprooted. A few pale tendrils "
             "remain here to 'gather'."),
            ("desc_depleted",
             "The hollow is bare — every windroot has been dug up. They "
             "will need time to regrow."),
        ],
    )

    rooms["mine_entrance"] = create_object(
        RoomBase,
        key="Mine Entrance",
        attributes=[
            ("desc",
             "A rough-hewn opening in the hillside, framed by cracked "
             "timber supports that lean inward at alarming angles. The "
             "boards that once sealed the entrance have been smashed aside "
             "— from the inside, judging by the splinters. A cold draft "
             "breathes from the darkness beyond, carrying the smell of "
             "damp stone, rust, and something sharper — animal musk. Crude "
             "scratches mark the rock face on either side of the entrance, "
             "too deliberate to be natural."),
        ],
    )
    rooms["mine_entrance"].details = {
        "timbers": (
            "The support timbers are cracked and bowing under the weight "
            "of the hillside. Fungus has eaten into the wood near the base, "
            "and the cross-beam overhead has a visible split running its "
            "full length. It looks stable enough, but not by much."
        ),
        "scratches": (
            "Crude pictographs scratched into the rock — stick figures "
            "with oversized heads, geometric shapes that might represent "
            "tunnels, and what looks like a territorial warning. Kobold "
            "markings."
        ),
    }

    # ── Upper Mine — Copper Level (5 rooms) ───────────────────────────

    rooms["entry_shaft"] = create_object(
        RoomBase,
        key="Entry Shaft",
        attributes=[
            ("desc",
             "The mine opens into a broad shaft cut straight into the "
             "rock. Timber supports line the walls at regular intervals, "
             "most still holding though some have buckled. The floor is "
             "gritty with crushed stone, and old torch brackets jut from "
             "the walls, empty and rusted. Scratches and crude marks cover "
             "the lower walls — kobold territory markers. Passages branch "
             "west into a copper-streaked drift and south into a timbered "
             "corridor."),
        ],
    )
    rooms["entry_shaft"].details = {
        "supports": (
            "Heavy pine timbers, squared with adze marks, brace the "
            "ceiling at six-foot intervals. Most are solid despite their "
            "age, though two have cracked and a third leans drunkenly, "
            "wedged in place by fallen rubble."
        ),
        "marks": (
            "Kobold claw-marks score the stone at knee height — territory "
            "boundaries, warnings, and what might be a crude count of "
            "something. Twelve groups of five scratches. Sixty of what?"
        ),
    }

    rooms["copper_drift"] = create_object(
        RoomHarvesting,
        key="Copper Drift",
        attributes=[
            ("desc",
             "A horizontal tunnel follows a vein of green-streaked rock. "
             "The walls glitter with native copper where pickaxes have "
             "exposed fresh surfaces, and the floor is littered with "
             "tailings. An old wheelbarrow, one wheel missing, sits "
             "tipped on its side. The drift continues deeper to the "
             "south."),
            ("resource_id", 23),
            ("resource_count", 0),
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "mine"),
            ("desc_abundant",
             "Green-streaked rock gives way to rich veins of native "
             "copper. There is plenty of copper ore to 'mine'."),
            ("desc_scarce",
             "Most of the copper has been extracted. A few greenish "
             "veins remain here to 'mine'."),
            ("desc_depleted",
             "The copper vein is spent — nothing but bare rock remains. "
             "New deposits will take time to be exposed."),
        ],
    )

    rooms["copper_seam"] = create_object(
        RoomHarvesting,
        key="Copper Seam",
        attributes=[
            ("desc",
             "The drift ends in a wide seam of copper ore, the richest "
             "part of the vein. Pickaxe marks show where miners once "
             "worked this face, and a rusted bucket sits half-full of "
             "ore chunks that someone never collected. The air is still "
             "and close."),
            ("resource_id", 23),
            ("resource_count", 0),
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "mine"),
            ("desc_abundant",
             "The copper seam is thick and generous, green-brown ore "
             "flaking free at every strike. Plenty to 'mine'."),
            ("desc_scarce",
             "The richest ore has been chipped away. A few pockets of "
             "copper remain in the seam to 'mine'."),
            ("desc_depleted",
             "The seam has been worked clean. Only bare rock and dust "
             "remain. Fresh deposits will need time to surface."),
        ],
    )

    rooms["timbered_corridor"] = create_object(
        RoomBase,
        key="Timbered Corridor",
        attributes=[
            ("desc",
             "A long passage runs south, its ceiling braced with heavy "
             "timber crossbeams. Rusted iron rails are set into the floor "
             "— an old ore cart track that once carried loads to the "
             "surface. The rails are bent in places where rock falls have "
             "twisted them. Kobold droppings and gnawed bones litter the "
             "edges of the passage."),
        ],
    )
    rooms["timbered_corridor"].details = {
        "rails": (
            "Narrow-gauge iron rails, pitted with rust, run the length "
            "of the corridor. The wooden sleepers beneath them have "
            "rotted in places, leaving sections of track unsupported "
            "and sagging."
        ),
        "bones": (
            "Small bones — rats, bats, maybe a rabbit — gnawed clean "
            "and discarded. Kobold leavings. They've been eating well "
            "down here."
        ),
    }

    rooms["ore_cart_track"] = create_object(
        RoomBase,
        key="Ore Cart Track",
        attributes=[
            ("desc",
             "The corridor widens around an overturned ore cart, its "
             "wooden body split and its iron wheels rusted in place. "
             "Spilled ore chunks have been kicked into the corners, and "
             "the rails here are buried under rubble. The passage south "
             "shows signs of frequent kobold traffic — the stone floor "
             "is worn smooth by clawed feet."),
        ],
    )
    rooms["ore_cart_track"].details = {
        "cart": (
            "The ore cart is a heavy wooden box on iron wheels, tipped "
            "on its side. The axle is snapped, and the wood has split "
            "along the grain. A few chunks of worthless quartz tumbled "
            "out when it fell and still lie scattered nearby."
        ),
    }

    # ── Kobold Territory (3 rooms) ────────────────────────────────────

    rooms["kobold_lookout"] = create_object(
        RoomBase,
        key="Kobold Lookout",
        attributes=[
            ("desc",
             "A natural widening in the tunnel has been turned into a "
             "kobold guard post. Crude barricades of piled stone and "
             "broken timber block the approaches, and a string of tin "
             "cans and animal bones spans the passage at ankle height — "
             "an alarm tripwire. The walls are covered in more kobold "
             "scratches, and the smell of their musty dens is strong. "
             "A side passage leads west to a flooded gallery, and a "
             "rough-cut shaft descends deeper into the mine."),
        ],
    )
    rooms["kobold_lookout"].details = {
        "barricade": (
            "Loose stones and broken pit-props piled waist-high, with "
            "gaps just wide enough for a kobold to squeeze through. "
            "Sharpened sticks poke outward from between the rocks — "
            "primitive but effective if you stumble into them."
        ),
        "tripwire": (
            "A length of frayed rope strung with tin cans, bones, and "
            "bits of scrap metal. Touch it and every kobold in earshot "
            "will know you're coming."
        ),
    }

    rooms["flooded_gallery"] = create_object(
        RoomBase,
        key="Flooded Gallery",
        attributes=[
            ("desc",
             "This side gallery has partially flooded where an "
             "underground spring broke through the rock. Dark water "
             "fills the lower half of the chamber, its surface still "
             "and oily. The ceiling is low and weeping with moisture, "
             "and the walls are slick with mineral deposits — green "
             "copper stains and white calcite crusts. Whatever was "
             "mined here is long since underwater."),
        ],
    )
    rooms["flooded_gallery"].details = {
        "water": (
            "The water is black and cold, reflecting nothing. It's "
            "impossible to tell how deep it goes. Something pale — a "
            "bone? a stone? — is just visible beneath the surface near "
            "the far wall."
        ),
    }

    rooms["descent_shaft"] = create_object(
        RoomBase,
        key="Descent Shaft",
        attributes=[
            ("desc",
             "A vertical shaft drops into deeper workings, with a "
             "rickety wooden ladder lashed to iron spikes driven into "
             "the rock face. The rungs are slick with moisture and "
             "several are missing entirely. Far below, a faint orange "
             "glow suggests torchlight — the kobolds have lit the "
             "lower levels. The air rising from below is warmer and "
             "carries the tang of worked metal."),
        ],
    )
    rooms["descent_shaft"].details = {
        "ladder": (
            "The ladder is a series of rough rungs lashed to two long "
            "poles with cord and wire. Three rungs are missing and two "
            "more flex dangerously underfoot. Someone has tied knots in "
            "a rope alongside it — a backup handhold, probably added by "
            "the kobolds given its height from the ground."
        ),
    }

    # ── Lower Mine — Tin Level (4 rooms) ──────────────────────────────

    rooms["lower_junction"] = create_object(
        RoomBase,
        key="Lower Junction",
        attributes=[
            ("desc",
             "At the base of the descent shaft, the mine opens into a "
             "junction of older tunnels. The air is warmer here, and "
             "crude torches burn in brackets — the kobolds maintain "
             "these. The stonework is rougher, the tunnels narrower, "
             "clearly dug by less skilled hands. Dark ore-streaked rock "
             "lines the walls. Passages branch east and west into tin "
             "workings, and a narrow tunnel leads south, deeper still."),
        ],
    )
    rooms["lower_junction"].details = {
        "torches": (
            "Crude torches made from bundled rags soaked in animal fat, "
            "jammed into rusted brackets. They burn with a smoky, "
            "unpleasant flame and leave streaks of soot on the ceiling. "
            "The kobolds replace them regularly — this is their domain."
        ),
    }

    rooms["tin_seam"] = create_object(
        RoomHarvesting,
        key="Tin Seam",
        attributes=[
            ("desc",
             "A low-ceilinged gallery follows a seam of dark, heavy "
             "ore through the rock. The tin deposits here show a dull "
             "metallic sheen where the rock has been freshly broken. "
             "Kobold digging tools — sharpened antlers and stone "
             "hammers — lie scattered about, suggesting the creatures "
             "have been working this vein themselves."),
            ("resource_id", 25),
            ("resource_count", 0),
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "mine"),
            ("desc_abundant",
             "Dark, heavy veins of tin ore cut through the rock with "
             "a dull metallic sheen. There is plenty to 'mine'."),
            ("desc_scarce",
             "Most of the tin has been chipped away. A few dull veins "
             "remain here to 'mine'."),
            ("desc_depleted",
             "The tin deposits are exhausted — only bare stone remains. "
             "New deposits will take time to be exposed."),
        ],
    )

    rooms["tin_vein"] = create_object(
        RoomHarvesting,
        key="Tin Vein",
        attributes=[
            ("desc",
             "A narrow tunnel ends at a wall of dark ore, the richest "
             "tin deposit in the mine. Pick marks — both human-sized "
             "and the smaller gouges of kobold tools — cover the rock "
             "face. A pile of sorted ore chunks sits in a corner, too "
             "heavy for the kobolds to carry far."),
            ("resource_id", 25),
            ("resource_count", 0),
            ("abundance_threshold", 3),
            ("harvest_height", 0),
            ("harvest_command", "mine"),
            ("desc_abundant",
             "A thick vein of tin ore runs through the rock face, dark "
             "and heavy. Plenty to 'mine'."),
            ("desc_scarce",
             "The richest ore has been taken. A few pockets of tin "
             "remain in the vein to 'mine'."),
            ("desc_depleted",
             "The vein has been worked clean. Only dust and bare rock "
             "remain. Fresh deposits will need time to surface."),
        ],
    )

    rooms["kobold_warren"] = create_object(
        RoomBase,
        key="Kobold Warren",
        attributes=[
            ("desc",
             "A natural cavern has been claimed as the kobolds' main "
             "den. Crude nests of shredded cloth, dried grass, and "
             "stolen blankets fill shallow hollows in the floor. The "
             "stench is powerful — musty fur, rotting food, and the "
             "acrid smell of their firepits. Stolen goods are piled "
             "against the walls: sacks of grain, mining tools, a "
             "cracked lantern, lengths of rope. A narrow passage south "
             "leads deeper, past a crude door of lashed boards."),
        ],
    )
    rooms["kobold_warren"].details = {
        "nests": (
            "Shallow depressions lined with whatever soft material the "
            "kobolds could steal or scavenge. Bits of wool blanket, "
            "straw, torn canvas, and clumps of animal fur. Each nest "
            "is roughly kobold-sized — small, but there are a lot of "
            "them."
        ),
        "goods": (
            "A haphazard hoard of stolen equipment. Mining picks with "
            "the handles chewed, half-empty grain sacks, coils of rope, "
            "a dented helmet, and a few tarnished coins. Nothing of "
            "great value, but the kobolds guard it fiercely."
        ),
    }

    # ── Deep Mine — Mystery (2 rooms) ─────────────────────────────────

    rooms["ancient_passage"] = create_object(
        RoomBase,
        key="Ancient Passage",
        attributes=[
            ("desc",
             "The rough-hewn mine tunnel gives way abruptly to something "
             "older and far more deliberate. The walls here are smooth, "
             "cut with a precision no pickaxe could achieve — fitted "
             "stone blocks joined without mortar, each one carved with "
             "faint geometric patterns that seem to shift at the edge "
             "of vision. The ceiling is vaulted, the floor level and "
             "even. Whatever civilisation built this, it was not the "
             "miners, and it was not the kobolds. The air is perfectly "
             "still and carries a faint hum, more felt than heard."),
        ],
    )
    rooms["ancient_passage"].details = {
        "walls": (
            "The stone blocks are enormous — each one taller than a man "
            "and fitted so precisely that a knife blade could not slip "
            "between them. The geometric patterns carved into their "
            "surfaces are shallow but intricate, repeating in ways that "
            "suggest meaning. They match nothing in any known tradition."
        ),
        "patterns": (
            "Interlocking circles and angular spirals, carved with a "
            "steady hand and inhuman patience. The same motifs appear "
            "in the deep sewers beneath Millholm — whoever built this "
            "passage also built those tunnels. How deep does it go?"
        ),
    }

    rooms["sealed_door"] = create_object(
        RoomBase,
        key="Sealed Door",
        attributes=[
            ("desc",
             "The passage ends at a massive stone door, twice the height "
             "of a man and carved from a single block of dark granite. "
             "Geometric glyphs cover its surface in concentric rings, "
             "radiating from a central depression shaped like no keyhole "
             "you have ever seen. There is no handle, no hinge, no "
             "visible mechanism. The stone is cold to the touch and "
             "faintly vibrates — the hum is strongest here. Whatever "
             "lies beyond this door, it has been sealed for a very "
             "long time."),
        ],
    )
    rooms["sealed_door"].details = {
        "glyphs": (
            "The glyphs are carved in concentric rings, spiralling "
            "inward toward the central depression. Some are worn smooth "
            "by time but most remain sharp-edged, as though the stone "
            "itself resists erosion. They glow faintly when touched, "
            "then fade."
        ),
        "depression": (
            "A shallow oval depression at the center of the door, "
            "perhaps six inches across. Not a keyhole — something "
            "else. The edges are polished smooth as glass, and the "
            "stone within is a slightly different shade, darker, as "
            "though a piece is missing. An artefact, perhaps, that "
            "once fit here."
        ),
        "door": (
            "You push against the stone. Nothing. You throw your "
            "shoulder into it. Nothing. The door does not budge, does "
            "not flex, does not even resonate with the impact. It is "
            "sealed beyond any strength you can bring to bear."
        ),
    }

    print(f"  Created {len(rooms)} rooms.")

    # ══════════════════════════════════════════════════════════════════
    # 2. CREATE EXITS
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # ── Surface connections ───────────────────────────────────────────
    connect(rooms["miners_camp"], rooms["windroot_hollow"], "north")
    connect(rooms["miners_camp"], rooms["mine_entrance"], "east")
    exit_count += 4

    # ── Upper Mine — Copper Level ─────────────────────────────────────
    connect(rooms["mine_entrance"], rooms["entry_shaft"], "east")
    connect(rooms["entry_shaft"], rooms["copper_drift"], "west")
    connect(rooms["copper_drift"], rooms["copper_seam"], "south")
    connect(rooms["entry_shaft"], rooms["timbered_corridor"], "south")
    connect(rooms["timbered_corridor"], rooms["ore_cart_track"], "south")
    exit_count += 10

    # ── Kobold Territory ──────────────────────────────────────────────
    connect(rooms["ore_cart_track"], rooms["kobold_lookout"], "south")
    connect(rooms["kobold_lookout"], rooms["flooded_gallery"], "west")
    connect(rooms["kobold_lookout"], rooms["descent_shaft"], "down")
    exit_count += 6

    # ── Lower Mine — Tin Level ────────────────────────────────────────
    connect(rooms["descent_shaft"], rooms["lower_junction"], "down")
    connect(rooms["lower_junction"], rooms["tin_seam"], "west")
    connect(rooms["lower_junction"], rooms["tin_vein"], "east")
    connect(rooms["lower_junction"], rooms["kobold_warren"], "south")
    exit_count += 8

    # ── Deep Mine — Mystery ───────────────────────────────────────────
    connect(rooms["kobold_warren"], rooms["ancient_passage"], "south")
    connect(rooms["ancient_passage"], rooms["sealed_door"], "south")
    exit_count += 4

    print(f"  Created {exit_count} exits.")

    # ══════════════════════════════════════════════════════════════════
    # 3. TAG ROOMS — zone, district, terrain
    # ══════════════════════════════════════════════════════════════════

    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # Surface rooms are forest terrain
    rooms["miners_camp"].set_terrain(TerrainType.FOREST.value)
    rooms["windroot_hollow"].set_terrain(TerrainType.FOREST.value)
    rooms["mine_entrance"].set_terrain(TerrainType.FOREST.value)

    # Mine interior is underground
    underground_keys = [
        "entry_shaft", "copper_drift", "copper_seam",
        "timbered_corridor", "ore_cart_track",
        "kobold_lookout", "flooded_gallery", "descent_shaft",
        "lower_junction", "tin_seam", "tin_vein", "kobold_warren",
        "ancient_passage", "sealed_door",
    ]
    for key in underground_keys:
        rooms[key].set_terrain(TerrainType.UNDERGROUND.value)

    print("  Tagged all rooms with zone, district, and terrain.")

    # ── Mob area tags — kobold territory ─────────────────────────────
    # Kobolds roam the mine interior from the lookout down through the
    # lower levels and warren. Not the surface rooms, entry shaft,
    # copper workings, or ancient passage / sealed door.
    kobold_rooms = [
        "timbered_corridor", "ore_cart_track",
        "kobold_lookout", "flooded_gallery", "descent_shaft",
        "lower_junction", "tin_seam", "tin_vein", "kobold_warren",
    ]
    for key in kobold_rooms:
        rooms[key].tags.add("mine_kobolds", category="mob_area")
    print(f"  Tagged {len(kobold_rooms)} rooms with mob_area=mine_kobolds.")

    # ══════════════════════════════════════════════════════════════════
    # 4. FUTURE CONNECTION NOTES
    # ══════════════════════════════════════════════════════════════════
    # miners_camp: procedural passages 3 & 4 (wired in build_game_world.py)
    #   ← west: proc passage 3 (inbound from deep_woods_clearing)
    #   → west: proc passage 4 (outbound back to deep_woods_clearing)
    # sealed_door: future content — pre-human underground ruins
    # flooded_gallery: possible hidden underwater passage (future)

    # ── District map cell tags ────────────────────────────────────────
    _mine_map_tags = {
        "mine_entrance":     "millholm_mine:mine_entrance",
        "entry_shaft":       "millholm_mine:entry_shaft",
        "copper_drift":      "millholm_mine:copper_drift",
        "copper_seam":       "millholm_mine:copper_seam",
        "timbered_corridor": "millholm_mine:timbered_corridor",
        "ore_cart_track":    "millholm_mine:ore_cart_track",
        "kobold_lookout":    "millholm_mine:kobold_lookout",
        "flooded_gallery":   "millholm_mine:flooded_gallery",
        "descent_shaft":     "millholm_mine:descent_shaft",
        "lower_junction":    "millholm_mine:lower_junction",
        "tin_seam":          "millholm_mine:tin_seam",
        "tin_vein":          "millholm_mine:tin_vein",
        "kobold_warren":     "millholm_mine:kobold_warren",
        "ancient_passage":   "millholm_mine:ancient_passage",
        "sealed_door":       "millholm_mine:sealed_door",
    }
    for room_key, tag in _mine_map_tags.items():
        rooms[room_key].tags.add(tag, category="map_cell")
    # ── Region map cell tags ──
    _rt = "millholm_region"
    # Mine entrance → region mine cell
    rooms["mine_entrance"].tags.add(f"{_rt}:mine_entrance", category="map_cell")
    for key in ["entry_shaft", "copper_drift", "copper_seam", "timbered_corridor",
                "ore_cart_track", "kobold_lookout", "flooded_gallery", "descent_shaft",
                "lower_junction", "tin_seam", "tin_vein", "kobold_warren",
                "ancient_passage", "sealed_door"]:
        rooms[key].tags.add(f"{_rt}:mine_dungeon", category="map_cell")
    # Windroot hollow → region farm (harvesting) cell
    rooms["windroot_hollow"].tags.add(f"{_rt}:windroot_hollow", category="map_cell")
    # Miners camp → deep woods NE (shared with faerie clearing)
    rooms["miners_camp"].tags.add(f"{_rt}:deep_woods_ne", category="map_cell")
    print(f"  Tagged {len(_mine_map_tags)} mine rooms with map_cell tags (district + region).")

    print("  Millholm Abandoned Mine complete.\n")
    return rooms

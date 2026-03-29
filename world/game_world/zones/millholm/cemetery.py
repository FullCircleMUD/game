"""
Millholm Cemetery — the burial ground west of the north road.

A 2x3 grid of graveyard rooms plus a gate room, connected west
off the north road. The central-east room is the RoomCemetery
bind point where players can bind their spirit for death respawn.

Layout:
    X   X
    |   |
    X   B -- G -- (north road)
    |   |
    X   X

Where B = bind room (RoomCemetery), G = gates, X = graveyard rooms.

Cross-district connection (north_road → cemetery_gates) is created
in soft_deploy.py after both town and cemetery are built.

Usage:
    from world.game_world.zones.millholm.cemetery import build_millholm_cemetery
    build_millholm_cemetery()
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_cemetery import RoomCemetery
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from utils.exit_helpers import connect, connect_door, connect_trapped_door


# ── Zone / district constants ─────────────────────────────────────────
ZONE = "millholm"
DISTRICT = "millholm_cemetery"


def build_millholm_cemetery():
    """Build the Millholm Cemetery district and return a dict of rooms."""
    rooms = {}

    print("  Building cemetery rooms...")

    # ══════════════════════════════════════════════════════════════════
    # GATE — entrance from the north road
    # ══════════════════════════════════════════════════════════════════

    rooms["cemetery_gates"] = create_object(
        RoomBase,
        key="Cemetery Track",
        attributes=[
            ("desc",
             "A narrow dirt track winds between overgrown hedgerows, the "
             "town falling away behind you. The path is quiet — just "
             "birdsong and the rustle of wind through long grass. Ahead, "
             "tall wrought-iron gates stand between stone pillars topped "
             "with weathered carvings of clasped hands, marking the "
             "entrance to the cemetery."),
            ("details", {
                "hedgerows": (
                    "Thick hawthorn hedges line both sides of the track, "
                    "their branches tangled and wild. White blossoms dot "
                    "the greenery in season, and birds nest deep within "
                    "the thorny cover."
                ),
                "pillars": (
                    "Stone gateposts topped with carvings of clasped hands, "
                    "worn smooth by weather. A name is carved into each "
                    "pillar but the letters are too eroded to read."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # BIND ROOM — the main cemetery with shrine (RoomCemetery)
    # ══════════════════════════════════════════════════════════════════

    rooms["cemetery"] = create_object(
        RoomCemetery,
        key="Millholm Cemetery",
        attributes=[
            ("bind_cost", 1),
            ("desc",
             "Ancient oaks shade rows of headstones that lean at tired "
             "angles in the long grass. Some graves are tended — fresh "
             "flowers, cleared weeds — while others have been forgotten, "
             "their inscriptions worn to nothing. A stone shrine near the "
             "centre allows the faithful to bind their spirit to this place "
             "of rest. Birdsong is the only sound. The town feels very far "
             "away."),
            ("details", {
                "shrine": (
                    "A small stone shrine, open on all sides, with a flat "
                    "altar stone at its centre. Candle stubs and dried "
                    "flower petals litter the surface. This is where the "
                    "dead are committed and where the living can bind their "
                    "spirit — so that death, when it comes, brings them back "
                    "here rather than somewhere less familiar."
                ),
                "headstones": (
                    "Rows of headstones in every state of repair. The oldest "
                    "are little more than rough stones with scratched letters. "
                    "The newest are carved granite with names, dates, and "
                    "brief epitaphs. 'Here lies Aldric Goldwheat, who fed "
                    "the town.' 'Mira Ironhand — she built what endures.'"
                ),
                "graves": (
                    "Rows of headstones in every state of repair. The oldest "
                    "are little more than rough stones with scratched letters. "
                    "The newest are carved granite with names, dates, and "
                    "brief epitaphs. 'Here lies Aldric Goldwheat, who fed "
                    "the town.' 'Mira Ironhand — she built what endures.'"
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # GRAVEYARD ROOMS — 5 rooms forming the rest of the 2x3 grid
    # ══════════════════════════════════════════════════════════════════

    rooms["graves_ne"] = create_object(
        RoomBase,
        key="Overgrown Graves",
        attributes=[
            ("desc",
             "This corner of the cemetery has been given over to nature. "
             "Ivy crawls across the headstones, and elder trees have "
             "forced their roots between the graves, tilting the stones "
             "at drunken angles. A blackbird sings from the top of a "
             "cracked obelisk. The names on the stones here are old — "
             "families that no longer live in Millholm."),
            ("details", {
                "obelisk": (
                    "A stone obelisk, cracked down one side and green "
                    "with lichen. The inscription reads 'The Ironhand "
                    "Family' but the individual names beneath have been "
                    "worn away by centuries of rain."
                ),
                "ivy": (
                    "Thick ropes of ivy wind across the graves, "
                    "binding the stones together. In places the ivy "
                    "has grown so thick it has split the mortar."
                ),
            }),
        ],
    )

    rooms["graves_nw"] = create_object(
        RoomBase,
        key="Untended Graves",
        attributes=[
            ("desc",
             "The graves here have been neglected for years. Weeds "
             "choke the paths between the plots, and several headstones "
             "have toppled face-down into the mud. A rusted iron railing "
             "surrounds what was once a family plot, but the gate has "
             "come off its hinges and lies half-buried in nettles. The "
             "air smells of damp earth and decay."),
            ("details", {
                "railing": (
                    "A rusted iron railing, once painted black, now "
                    "flaking orange. The posts are set in crumbling "
                    "stone bases. This was a prosperous family's plot, "
                    "once upon a time."
                ),
                "toppled stones": (
                    "Several headstones have fallen forward onto their "
                    "faces. The earth beneath them has subsided — the "
                    "graves are sinking."
                ),
            }),
        ],
    )

    rooms["graves_e"] = create_object(
        RoomBase,
        key="Tended Graves",
        attributes=[
            ("desc",
             "This section of the cemetery is well-maintained. The grass "
             "between the graves is trimmed, fresh flowers sit in stone "
             "vases, and the headstones are clean. These are the recent "
             "dead — the dates carved into the granite are only years "
             "old. A wooden bench sits beneath a yew tree, placed for "
             "those who come to remember."),
            ("details", {
                "bench": (
                    "A simple wooden bench beneath a spreading yew tree. "
                    "The seat is worn smooth by use. Someone has carved "
                    "a small heart into one arm."
                ),
                "flowers": (
                    "Fresh wildflowers in stone vases — cornflowers, "
                    "daisies, and sprigs of rosemary for remembrance. "
                    "Someone visits regularly."
                ),
            }),
        ],
    )

    rooms["graves_se"] = create_object(
        RoomBase,
        key="Paupers' Corner",
        attributes=[
            ("desc",
             "The far corner of the cemetery, where the headstones are "
             "smaller and simpler — or absent altogether. Wooden crosses, "
             "some with names scratched into them, mark the graves of "
             "those who couldn't afford stone. A few unmarked mounds "
             "of earth sit at the very edge, where the cemetery gives "
             "way to wild scrubland. Even in death, there is a hierarchy."),
            ("details", {
                "crosses": (
                    "Simple wooden crosses, some barely more than two "
                    "sticks lashed together. A few have names scratched "
                    "into the wood with a knife. Others are blank."
                ),
                "mounds": (
                    "Low mounds of earth, unmarked. Whoever lies here "
                    "had nobody to carve a name for them."
                ),
            }),
        ],
    )

    rooms["graves_sw"] = create_object(
        RoomBase,
        key="Old Crypts",
        attributes=[
            ("desc",
             "Stone crypts and mausoleums line the western wall of the "
             "cemetery, their heavy doors sealed with iron bands. These "
             "are the oldest structures here — built when Millholm was "
             "young and its founding families wanted to be remembered "
             "forever. Carved angels and weeping figures adorn the "
             "facades, though time has worn their features soft. Moss "
             "grows thick on the north-facing walls."),
            ("details", {
                "crypts": (
                    "Heavy stone structures with iron-banded doors, "
                    "each bearing a family name above the lintel. "
                    "Stonefield. Goldwheat. Ironhand. The doors are "
                    "sealed and haven't been opened in living memory."
                ),
                "angels": (
                    "Stone angels carved into the facades of the crypts. "
                    "Their faces have been worn smooth by centuries of "
                    "rain, giving them a blank, eyeless look that is "
                    "deeply unsettling after dark."
                ),
            }),
        ],
    )

    # ══════════════════════════════════════════════════════════════════
    # FAMILY TOMBS — west of the west column
    # ══════════════════════════════════════════════════════════════════

    # ── Stonefield Tomb (3 rooms — trap, door, boss) ─────────────────

    rooms["tomb_stonefield"] = create_object(
        RoomBase,
        key="Stonefield Tomb - Antechamber",
        attributes=[
            ("desc",
             "A low stone chamber, cold and close. The air is stale "
             "and heavy with the smell of old dust and dry rot. The "
             "walls are lined with niches, each holding a stone urn "
             "inscribed with a name and dates. Cobwebs hang from the "
             "ceiling in thick curtains. The Stonefield family crest — "
             "a ship under sail above a pair of crossed keys — is "
             "carved into the back wall. The floor is suspiciously "
             "clean in one spot, the dust disturbed."),
            ("details", {
                "urns": (
                    "Stone urns in wall niches, each bearing a name "
                    "in faded gold lettering. Aldric Stonefield. Maren "
                    "Stonefield. Tobias Stonefield. The older ones are "
                    "cracked and stained."
                ),
                "crest": (
                    "The Stonefield family crest: a merchant ship under "
                    "full sail above a pair of crossed keys. An odd "
                    "choice for a family of traders — the keys suggest "
                    "something locked away, something hidden."
                ),
                "floor": (
                    "The dust on the floor has been disturbed here — "
                    "scuff marks and the faint outline of a pressure "
                    "plate set into the flagstones."
                ),
            }),
        ],
    )

    rooms["tomb_stonefield_inner"] = create_object(
        RoomBase,
        key="Stonefield Tomb - Inner Passage",
        attributes=[
            ("desc",
             "A narrow passage cut from the rock, leading deeper "
             "beneath the cemetery. The stonework here is older and "
             "rougher than the antechamber — this part of the tomb "
             "was carved long before the rest. Iron brackets on the "
             "walls once held torches, now empty. The air is colder "
             "here, and there is a faint sound — a dry, scratching "
             "rustle from somewhere ahead."),
            ("details", {
                "stonework": (
                    "Rough-hewn stone, much older than the polished "
                    "blocks of the antechamber. Tool marks from ancient "
                    "chisels are still visible. This passage predates "
                    "Millholm itself."
                ),
                "sound": (
                    "A dry, rhythmic scratching from somewhere deeper "
                    "in the tomb. Like bone on stone."
                ),
            }),
        ],
    )

    rooms["tomb_stonefield_burial"] = create_object(
        RoomBase,
        key="Stonefield Burial Chamber",
        attributes=[
            ("desc",
             "A vaulted chamber of dark stone, the ceiling lost in "
             "shadow. Three stone sarcophagi stand on raised platforms "
             "against the walls, their lids carved with the likenesses "
             "of the dead within — stern faces, folded hands, merchant "
             "robes. The central sarcophagus is larger and more ornate "
             "than the others, its lid slightly ajar. Something has "
             "been in here. Something that moved the lid. Scratch marks "
             "on the stone floor lead from the sarcophagi to the "
             "doorway and back again."),
            ("details", {
                "sarcophagi": (
                    "Three stone coffins, each carved from a single "
                    "block of granite. The central one bears the name "
                    "'ALDRIC STONEFIELD — FOUNDER' in deep-cut letters. "
                    "Its lid is cracked and sits slightly askew, as if "
                    "pushed from within."
                ),
                "scratch marks": (
                    "Deep scratches gouged into the flagstone floor, "
                    "running from the base of the sarcophagi to the "
                    "doorway. Whatever made them had hard, sharp points "
                    "for feet. Or fingers."
                ),
                "lid": (
                    "The lid of the central sarcophagus is ajar — "
                    "pushed a few inches to one side. The gap is "
                    "dark. You could look inside, but you'd have to "
                    "reach in."
                ),
            }),
        ],
    )

    # ── Goldwheat Tomb (1 room — flavour only) ──────────────────────

    rooms["tomb_goldwheat"] = create_object(
        RoomBase,
        key="Goldwheat Family Tomb",
        attributes=[
            ("desc",
             "A modest stone chamber, warmer and drier than expected. "
             "Sheaves of carved wheat adorn the walls, and the family "
             "motto — 'From the Earth, For the People' — is inscribed "
             "above the entrance. Four stone sarcophagi rest in alcoves, "
             "their lids sealed with lead and undisturbed. Fresh "
             "wildflowers have been placed on each one — someone still "
             "visits. The air smells faintly of dry grain and candle "
             "wax."),
            ("details", {
                "sarcophagi": (
                    "Four sealed stone coffins in wall alcoves. Each "
                    "bears a name: Aldric Goldwheat, Brenna Goldwheat, "
                    "Thom Goldwheat, Little Miri Goldwheat. The last "
                    "is heartbreakingly small."
                ),
                "flowers": (
                    "Fresh wildflowers — cornflowers and daisies — "
                    "laid carefully on each sarcophagus. Someone has "
                    "been here recently. The Goldwheat family still "
                    "remembers its dead."
                ),
                "wheat": (
                    "Carved sheaves of wheat, beautifully detailed, "
                    "covering every wall. Each stalk is individually "
                    "rendered. The stonemason loved this work."
                ),
            }),
        ],
    )

    # ── Ironhand Crypt (1 room — flavour only) ──────────────────────

    rooms["tomb_ironhand"] = create_object(
        RoomBase,
        key="Ironhand Family Crypt",
        attributes=[
            ("desc",
             "A martial chamber of dark stone. Weapons and shields "
             "are mounted on the walls between the burial niches — "
             "rusted swords, dented helms, a shattered shield bearing "
             "a clenched fist. The Ironhand family were soldiers and "
             "smiths, and even in death they are surrounded by iron. "
             "The sarcophagi here are plain and unadorned — no carved "
             "faces, no fine lettering. Just names, ranks, and dates. "
             "A soldier's burial."),
            ("details", {
                "weapons": (
                    "Ancient weapons mounted on the walls. A notched "
                    "longsword, a battleaxe with a cracked haft, a "
                    "round shield split nearly in two. These were "
                    "carried in real fights, not made for display."
                ),
                "sarcophagi": (
                    "Plain stone coffins with simple inscriptions. "
                    "'Sergeant Bram Ironhand.' 'Captain Hilde Ironhand.' "
                    "'Ironhand the Elder — She Built What Endures.' "
                    "No flowers, no ornament. Soldiers don't need them."
                ),
                "fist": (
                    "The Ironhand crest — a clenched iron fist on a "
                    "field of black. It appears on the shattered shield "
                    "and is carved above the entrance. The knuckles "
                    "are scarred, even in stone."
                ),
            }),
        ],
    )

    print(f"  Created {len(rooms)} cemetery rooms.")

    # ══════════════════════════════════════════════════════════════════
    # EXITS
    # ══════════════════════════════════════════════════════════════════

    exit_count = 0

    # Gate → Cemetery (wrought-iron gates)
    connect_door(
        rooms["cemetery_gates"], rooms["cemetery"], "west",
        key="wrought-iron gates",
        door_name="gates",
        closed_ab=(
            "Tall wrought-iron gates bar the entrance to the cemetery. "
            "Their bars are worked into patterns of ivy and wheat."
        ),
        open_ab=(
            "The iron gates stand open, revealing rows of headstones "
            "among long grass and ancient oaks."
        ),
        closed_ba=(
            "Wrought-iron gates close off the track back to town. "
            "Their hinges are well-oiled."
        ),
        open_ba=(
            "The gates stand open. A dirt track leads east toward "
            "the town."
        ),
    )
    exit_count += 2

    # 2x3 grid:
    #   NW -- NE
    #   |     |
    #   W  -- B  -- G
    #   |     |
    #   SW -- SE

    # East column N-S
    connect(rooms["graves_ne"], rooms["cemetery"], "south")
    connect(rooms["cemetery"], rooms["graves_se"], "south")

    # West column N-S
    connect(rooms["graves_nw"], rooms["graves_e"], "south")
    connect(rooms["graves_e"], rooms["graves_sw"], "south")

    # East-West rows
    connect(rooms["graves_nw"], rooms["graves_ne"], "east")
    connect(rooms["graves_e"], rooms["cemetery"], "east")
    connect(rooms["graves_sw"], rooms["graves_se"], "east")

    exit_count += 14  # 7 bidirectional pairs

    # Family tombs — doors west off the west column
    connect_door(
        rooms["graves_nw"], rooms["tomb_stonefield"], "west",
        key="a stone door",
        closed_ab="A heavy stone door bears the Stonefield crest — a ship above crossed keys.",
        open_ab="The Stonefield tomb lies open, cold air drifting from within.",
        closed_ba="A heavy stone door leads east to the cemetery.",
        open_ba="Daylight filters through the open door.",
        door_name="stone door",
    )
    connect_door(
        rooms["graves_e"], rooms["tomb_goldwheat"], "west",
        key="a stone door",
        closed_ab="A stone door carved with sheaves of wheat marks the Goldwheat family tomb.",
        open_ab="The Goldwheat tomb stands open, the smell of candle wax drifting out.",
        closed_ba="A stone door leads east to the cemetery.",
        open_ba="The cemetery is visible through the open door.",
        door_name="stone door",
    )
    connect_door(
        rooms["graves_sw"], rooms["tomb_ironhand"], "west",
        key="a stone door",
        closed_ab="A stone door bearing a clenched iron fist marks the Ironhand family crypt.",
        open_ab="The Ironhand crypt lies open, the glint of old weapons visible within.",
        closed_ba="A stone door leads east to the cemetery.",
        open_ba="The cemetery is visible through the open door.",
        door_name="stone door",
    )
    exit_count += 6

    # Stonefield tomb interior — trapped iron door → inner passage
    connect_trapped_door(
        rooms["tomb_stonefield"], rooms["tomb_stonefield_inner"], "west",
        key="an iron door",
        closed_ab="A rusted iron door blocks the passage deeper into the tomb.",
        open_ab="The iron door stands open, revealing a dark passage beyond.",
        closed_ba="A rusted iron door blocks the way east.",
        open_ba="The antechamber is visible through the open door.",
        door_name="iron door",
        trap_find_dc=8,
        trap_disarm_dc=8,
        trap_damage_dice="1d4",
        trap_damage_type="piercing",
        trap_description="a set of rusted dart tubes hidden in the door frame",
        trap_one_shot=True,
        trap_side="ab",
    )
    exit_count += 2

    # Tripwire between inner passage and burial chamber
    from typeclasses.terrain.exits.exit_tripwire import TripwireExit

    tripwire_ab = create_object(
        TripwireExit,
        key="Stonefield Burial Chamber",
        location=rooms["tomb_stonefield_inner"],
        destination=rooms["tomb_stonefield_burial"],
    )
    tripwire_ab.set_direction("west")
    tripwire_ab.is_trapped = True
    tripwire_ab.trap_armed = True
    tripwire_ab.trap_find_dc = 8
    tripwire_ab.trap_disarm_dc = 8
    tripwire_ab.trap_damage_dice = "1d4"
    tripwire_ab.trap_damage_type = "piercing"
    tripwire_ab.trap_description = "a thin wire stretched across the passage"
    tripwire_ab.trap_one_shot = True

    # Return exit from burial chamber (no trap)
    exit_burial_back = create_object(
        ExitVerticalAware,
        key="Inner Passage",
        location=rooms["tomb_stonefield_burial"],
        destination=rooms["tomb_stonefield_inner"],
    )
    exit_burial_back.set_direction("east")
    exit_count += 2

    print(f"  Created {exit_count} cemetery exits.")

    # ══════════════════════════════════════════════════════════════════
    # TAGS — zone, district, terrain, properties
    # ══════════════════════════════════════════════════════════════════

    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")

    # Outdoor rooms — cemetery grounds (max_height 1, weather-exposed)
    outdoor = [
        rooms["cemetery_gates"], rooms["cemetery"],
        rooms["graves_ne"], rooms["graves_nw"],
        rooms["graves_e"], rooms["graves_se"], rooms["graves_sw"],
    ]
    for room in outdoor:
        room.set_terrain(TerrainType.RURAL.value)
        room.sheltered = False
        room.max_height = 1

    # Indoor rooms — family tombs (max_height 0, underground)
    tombs = [
        rooms["tomb_stonefield"], rooms["tomb_stonefield_inner"],
        rooms["tomb_stonefield_burial"],
        rooms["tomb_goldwheat"], rooms["tomb_ironhand"],
    ]
    for room in tombs:
        room.set_terrain(TerrainType.UNDERGROUND.value)
        room.max_height = 0

    # Mob area tag for zone spawn script
    rooms["tomb_stonefield_burial"].tags.add(
        "cemetery_tomb", category="mob_area",
    )

    # ══════════════════════════════════════════════════════════════════
    # LOOT — coffin in the burial chamber
    # ══════════════════════════════════════════════════════════════════

    from typeclasses.world_objects.chest import WorldChest

    coffin = create.create_object(
        WorldChest,
        key="a stone sarcophagus",
        location=rooms["tomb_stonefield_burial"],
        nohome=True,
    )
    coffin.db.desc = (
        "The central sarcophagus — the largest and most ornate. Its "
        "heavy granite lid has been pushed partly aside, revealing "
        "darkness within. The name 'ALDRIC STONEFIELD — FOUNDER' is "
        "carved deep into the stone. Whatever is inside has been "
        "undisturbed for centuries."
    )
    coffin.loot_gold_max = 10
    coffin.spawn_scrolls_max = {"basic": 1}
    coffin.tags.add(ZONE, category="zone")
    coffin.tags.add(DISTRICT, category="district")

    print("  Placed lootable sarcophagus in Stonefield Burial Chamber.")

    # District map cell tags — cemetery appears on the town map
    rooms["cemetery_gates"].tags.add("millholm_town:cemetery_gates", category="map_cell")
    rooms["cemetery"].tags.add("millholm_town:cemetery", category="map_cell")
    # Region map cell tag — cemetery is its own cell on the region map
    for room in rooms.values():
        room.tags.add("millholm_region:cemetery", category="map_cell")

    print("  Tagged all cemetery rooms (zone, district, terrain, weather).")
    print("  Millholm Cemetery complete.\n")

    return rooms

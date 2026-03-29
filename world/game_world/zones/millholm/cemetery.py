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
from utils.exit_helpers import connect, connect_door


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

    print(f"  Created {exit_count} cemetery exits.")

    # ══════════════════════════════════════════════════════════════════
    # TAGS — zone, district, terrain, properties
    # ══════════════════════════════════════════════════════════════════

    for room in rooms.values():
        room.tags.add(ZONE, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.RURAL.value)
        room.sheltered = False  # outdoor, weather-exposed
        # Dark at night — no lampposts in a cemetery

    print("  Tagged all cemetery rooms (zone, district, terrain, weather).")
    print("  Millholm Cemetery complete.\n")

    return rooms

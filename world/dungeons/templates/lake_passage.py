"""
Lake Passage — procedural passage connecting the Lake Track to the
Lake Shore through scrubland north of Millholm.

The terrain transitions from rough track to open scrub to lakeside
meadow as the player moves north toward the lake. Light, open terrain
— no dense forest, no darkness. Gorse, heather, bracken, and
wildflowers.

Group mode, boss_depth=5 (5 rooms of scrubland before the shore).
Low branching — a winding track, not a maze.
"""

import random

from evennia import create_object

from world.dungeons import register_dungeon
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Room descriptions by depth — scrubland transitioning to lakeside
# ------------------------------------------------------------------ #

_NEAR_DESCS = [
    "The road has given way to a rough track through low scrubland. "
    "Gorse bushes crowd the path on either side, their yellow flowers "
    "bright against the grey-green foliage. Rabbits scatter at your "
    "approach.",
    "A dirt track winds between patches of bracken and heather. The "
    "ground is uneven and pocked with rabbit holes. The town is "
    "already out of sight behind a low rise.",
    "Rough grassland stretches away on either side of the path. A "
    "dry-stone wall, half-collapsed, marks where someone once tried "
    "to farm this land and gave up. Skylarks trill overhead.",
]

_MID_DESCS = [
    "The scrub thins out here, giving way to rough meadow dotted with "
    "wildflowers. The air is fresher — there's a dampness to it that "
    "hints at water nearby. The track is barely visible, just a faint "
    "line through the grass.",
    "Low rolling hills of coarse grass and clover. A few stunted "
    "hawthorn trees lean away from the prevailing wind, their branches "
    "bent into permanent submission. The ground is softer underfoot.",
    "The path crosses a shallow ditch choked with bulrushes and flags. "
    "Dragonflies hover over the standing water. The land is flattening "
    "out, and the air carries a faint mineral smell.",
]

_LAKE_DESCS = [
    "The ground grows marshy here, the grass giving way to tussocks "
    "and sedge. Water glints between the hummocks. The track picks "
    "its way along the drier ground, marked by old wooden stakes "
    "driven into the mud.",
    "Reeds and rushes crowd the path as the ground slopes gently "
    "downward. The sound of lapping water is close now, and wading "
    "birds stalk through the shallows. The air smells of clean water "
    "and wet earth.",
]

_ROOM_NAMES = [
    "Scrubland Track",
    "Rough Meadow",
    "Overgrown Path",
    "Heather Moor",
    "Marshy Ground",
    "Lakeside Trail",
]


def _get_room_desc(depth):
    """Get a room description based on depth."""
    if depth <= 1:
        return random.choice(_NEAR_DESCS)
    elif depth <= 3:
        return random.choice(_MID_DESCS)
    else:
        return random.choice(_LAKE_DESCS)


# ------------------------------------------------------------------ #
#  Room generator
# ------------------------------------------------------------------ #

def generate_lake_passage_room(instance, depth, coords):
    """Create a scrubland passage room."""
    from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

    name = random.choice(_ROOM_NAMES)
    desc = _get_room_desc(depth)

    room = create_object(
        DungeonRoom,
        key=name,
    )
    room.db.desc = desc
    return room


# ------------------------------------------------------------------ #
#  Template registration
# ------------------------------------------------------------------ #

LAKE_PASSAGE = DungeonTemplate(
    template_id="lake_passage",
    name="Lake Passage",
    dungeon_type="passage",
    instance_mode="shared",
    boss_depth=5,
    max_unexplored_exits=2,
    max_new_exits_per_room=1,       # low branching — winding track
    instance_lifetime_seconds=3600,  # 1 hour, then resets when empty
    empty_collapse_delay=0,          # collapse immediately when empty after lifetime
    room_generator=generate_lake_passage_room,
    boss_generator=None,             # passage type — no boss
    room_typeclass="typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom",
    allow_combat=True,
    allow_pvp=False,
    allow_death=False,
    terrain_type="plains",
)

register_dungeon(LAKE_PASSAGE)

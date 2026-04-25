"""
Southern Woods Passage — procedural passage connecting static landmarks
in the Millholm southern woods.

Used for the hidden paths between the main forest grids and the four
mini-areas (bandit camp, two moonpetal clearings, raven-cursed sage's
hut), and for the sibling connections between paired mini-areas.

Group mode, boss_depth=4 (short passages), branchy settings to create
a maze-like feel (max 3 new exits per room, up to 5 live unexplored
exits at any time) so players can wander and feel dynamic terrain
rather than a single winding trail.
"""

import random

from evennia import create_object

from world.dungeons import register_dungeon
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Room descriptions by depth
# ------------------------------------------------------------------ #

_SHALLOW_DESCS = [
    "The trail peters out into a tangle of undergrowth. Fern and "
    "bracken crowd between the trunks, and animal runs thread away "
    "in several directions. It is easy to get turned around here.",
    "Dense woods close overhead, the canopy knotted so tight the "
    "light is perpetually dim. Paths — if they can be called that — "
    "branch and rejoin through the ferns, and every gap between "
    "trees looks like it might lead somewhere.",
    "The woods are thick and old. Moss-slicked roots hump across "
    "the ground, making every step uncertain, and the trees seem "
    "to press closer the further you go.",
]

_MID_DESCS = [
    "The woods grow wilder. Fallen trunks lie across one another "
    "in slow collapses, and mushroom-ringed hollows between the "
    "roots could hide anything. The sense of direction is gone.",
    "The canopy is so dense the ground never fully dries. The "
    "earth squelches underfoot and the air is thick with the smell "
    "of leaf-mould and wet bark. Every direction looks the same.",
    "Briars crowd the narrow game-runs, and the trees are taller "
    "here, their lower branches stripped of leaves by something "
    "that climbs. You feel watched.",
]

_DEEP_DESCS = [
    "Deep in the southern woods. The trees are ancient and "
    "knotted, and the undergrowth between them is patchy but "
    "treacherous — roots and sinkholes and tangles of thorn. "
    "Something has been through here recently.",
    "The forest is dense and close. Faint game trails twist "
    "between the trunks, and the light is green and shifting. "
    "Any direction could lead somewhere, or nowhere.",
]

_ROOM_NAMES = [
    "Dense Woods",
    "Tangled Thicket",
    "Game Runs",
    "Forest Hollow",
    "Twisted Roots",
    "Overgrown Path",
    "Shadowed Grove",
]


def _get_room_desc(depth):
    """Get a room description based on depth."""
    if depth <= 1:
        return random.choice(_SHALLOW_DESCS)
    elif depth <= 2:
        return random.choice(_MID_DESCS)
    else:
        return random.choice(_DEEP_DESCS)


# ------------------------------------------------------------------ #
#  Room generator
# ------------------------------------------------------------------ #

def generate_southern_woods_room(instance, depth, coords):
    """
    Create a southern woods passage room.

    Args:
        instance: DungeonInstanceScript
        depth: Manhattan distance from origin
        coords: (x, y) tuple
    Returns:
        DungeonRoom object
    """
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

SOUTHERN_WOODS_PASSAGE = DungeonTemplate(
    template_id="southern_woods_passage",
    name="Southern Woods Passage",
    dungeon_type="passage",
    instance_mode="group",
    boss_depth=4,                     # short passages
    max_unexplored_exits=5,           # several live branches at once
    max_new_exits_per_room=3,         # branchy / maze-like
    instance_lifetime_seconds=7200,
    room_generator=generate_southern_woods_room,
    boss_generator=None,              # passage type — no boss
    room_typeclass="typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom",
    allow_combat=True,
    allow_pvp=False,
    allow_death=False,
    terrain_type="forest",
)

register_dungeon(SOUTHERN_WOODS_PASSAGE)

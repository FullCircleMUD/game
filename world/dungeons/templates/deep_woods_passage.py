"""
Deep Woods Passage — procedural passage connecting two static rooms
through the deep woods.

Used for:
  - deep_woods_entry → deep_woods_clearing (passage 1: inbound)
  - deep_woods_clearing → deep_woods_entry (passage 2: outbound/return)

Group mode, boss_depth=5 (5 rooms of dense forest before exit).
Low branching (max 1 new exit per room) — a winding trail, not a maze.
Passages despawn after the group exits.
"""

import random

from evennia import create_object

from world.dungeons import register_dungeon
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Room descriptions by depth — progressively darker / denser
# ------------------------------------------------------------------ #

_SHALLOW_DESCS = [
    "The trees close in overhead, their branches woven so tightly that "
    "only thin shafts of grey light reach the ground. The air is damp "
    "and still, heavy with the smell of leaf mould.",
    "A narrow gap between ancient oaks leads deeper into the forest. "
    "The undergrowth is thick and tangled, forcing a winding path "
    "through walls of fern and briar.",
    "Moss-slicked roots snake across the trail, making each step "
    "treacherous. The forest is eerily quiet — no birdsong, no "
    "insect drone, only the creak of wood.",
]

_MID_DESCS = [
    "The canopy is so dense here that it might as well be twilight. "
    "Pale fungi glow faintly on the trunks of dead trees, and the "
    "ground squelches underfoot. Something moved in the shadows.",
    "The path — if it can be called that — threads between trees so "
    "old their bark has turned black and hard as iron. Cobwebs thick "
    "as gauze stretch between the branches.",
    "A tangle of fallen trunks forces a scramble over slippery wood. "
    "The air tastes of rot and rain. Somewhere in the darkness ahead, "
    "something breathes.",
]

_DEEP_DESCS = [
    "The forest is utterly dark here. Ancient trunks rise like pillars "
    "in a vast, lightless hall. The ground is soft with centuries of "
    "undisturbed decay. Every sound is swallowed.",
    "Gnarled roots erupt from the earth like frozen serpents, and the "
    "trees lean together as if conferring in whispers. The air is "
    "thick, cold, and smells of deep earth and old stone.",
    "The woods have gone wrong here — trees grow at impossible angles, "
    "their branches knotted into shapes that almost resemble faces. "
    "The silence has weight.",
]

_ROOM_NAMES = [
    "Deep Woods",
    "Dark Forest Trail",
    "Overgrown Path",
    "Shadowed Thicket",
    "Tangled Depths",
    "Lightless Wood",
]


def _get_room_desc(depth):
    """Get a room description based on depth."""
    if depth <= 1:
        return random.choice(_SHALLOW_DESCS)
    elif depth <= 3:
        return random.choice(_MID_DESCS)
    else:
        return random.choice(_DEEP_DESCS)


# ------------------------------------------------------------------ #
#  Room generator
# ------------------------------------------------------------------ #

def generate_deep_woods_room(instance, depth, coords):
    """
    Create a deep woods passage room.

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

DEEP_WOODS_PASSAGE = DungeonTemplate(
    template_id="deep_woods_passage",
    name="Deep Woods Passage",
    dungeon_type="passage",
    instance_mode="group",
    boss_depth=5,
    max_unexplored_exits=2,
    max_new_exits_per_room=1,       # low branching — winding trail
    instance_lifetime_seconds=7200,  # 2 hours
    room_generator=generate_deep_woods_room,
    boss_generator=None,             # passage type — no boss
    room_typeclass="typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom",
    allow_combat=True,
    allow_pvp=False,
    allow_death=False,
    terrain_type="forest",
)

register_dungeon(DEEP_WOODS_PASSAGE)

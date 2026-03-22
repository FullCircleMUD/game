"""
Cave of Trials — a test dungeon template for development.

Uses boss_depth=3 for quick testing. Rooms get progressively darker
descriptions as depth increases.
"""

import random

from evennia import create_object

from world.dungeons import register_dungeon
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Room descriptions by depth
# ------------------------------------------------------------------ #

_SHALLOW_DESCS = [
    "A narrow cave passage. Water drips from the ceiling, and the air "
    "smells of damp earth. Rough-hewn walls glisten in the dim light.",
    "A low tunnel carved by ancient water. Patches of luminous moss cling "
    "to the walls, casting a faint greenish glow.",
    "A small cavern where the passage widens briefly. Stalactites hang "
    "overhead like stone teeth.",
]

_MID_DESCS = [
    "The cave grows darker and the air thicker. Strange scratches mark "
    "the walls — claw marks, perhaps. Something lives down here.",
    "A twisting passage with unstable footing. Loose stones clatter "
    "underfoot, echoing into the darkness ahead.",
    "An underground chamber with a low ceiling. The bones of small "
    "creatures litter the floor.",
]

_DEEP_DESCS = [
    "The darkness here is oppressive. Your torchlight barely reaches "
    "the walls. A low, rhythmic rumbling echoes from somewhere below.",
    "A vast cavern opens before you. The ceiling vanishes into darkness. "
    "The ground is scored with deep gouges.",
]

_BOSS_DESC = (
    "A massive underground chamber, its ceiling lost in shadow. "
    "The floor is scarred and blackened. In the centre, something "
    "enormous stirs, awakened by your intrusion."
)

_ROOM_NAMES_BY_DEPTH = {
    0: "Cave Entrance",
    1: "Shallow Passage",
    2: "Winding Tunnel",
}


def _get_room_name(depth):
    """Get a room name based on depth."""
    if depth in _ROOM_NAMES_BY_DEPTH:
        return _ROOM_NAMES_BY_DEPTH[depth]
    return "Deep Cavern"


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

def generate_cave_room(instance, depth, coords):
    """
    Create a cave dungeon room.

    Args:
        instance: DungeonInstanceScript
        depth: Manhattan distance from origin
        coords: (x, y) tuple
    Returns:
        DungeonRoom object
    """
    from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

    name = _get_room_name(depth)
    desc = _get_room_desc(depth)

    room = create_object(
        DungeonRoom,
        key=name,
    )
    room.db.desc = desc
    return room


# ------------------------------------------------------------------ #
#  Boss generator
# ------------------------------------------------------------------ #

def generate_cave_boss(instance, room):
    """
    Spawn the cave boss in the boss room.

    For now, creates a simple NPC placeholder. Once the combat system
    is implemented, this will create a proper combat mob.

    Args:
        instance: DungeonInstanceScript
        room: The boss room
    Returns:
        Boss NPC object (or None)
    """
    from typeclasses.actors.npc import BaseNPC

    room.db.desc = _BOSS_DESC
    room.key = "BINGO!"
    room.quest_tags = ["thief_initiation"]

    boss = create_object(
        BaseNPC,
        key="Cave Troll",
        location=room,
    )
    boss.db.desc = (
        "A massive cave troll, its grey hide scarred from countless "
        "battles. It towers over you, club in hand, red eyes gleaming "
        "with malice."
    )
    boss.is_immortal = False
    boss.level = 5

    return boss


# ------------------------------------------------------------------ #
#  Template registration
# ------------------------------------------------------------------ #

CAVE_OF_TRIALS = DungeonTemplate(
    template_id="cave_of_trials",
    name="The Cave of Trials",
    dungeon_type="instance",
    instance_mode="group",
    boss_depth=5,
    max_unexplored_exits=2,
    max_new_exits_per_room=2,
    instance_lifetime_seconds=7200,  # 2 hours
    room_generator=generate_cave_room,
    boss_generator=generate_cave_boss,
    room_typeclass="typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom",
    allow_combat=True,
    allow_pvp=False,
    allow_death=False,
    post_boss_linger_seconds=300,  # 5 minutes
)

register_dungeon(CAVE_OF_TRIALS)

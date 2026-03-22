"""
Rat Cellar — 1-room instanced dungeon for the Harvest Moon cellar quest.

The game's first combat encounter. A solo instance spawns 3 cellar rats
and a Rat King in a single room. No forward exits — the entire dungeon
is one room that the player fights through.

No-death: defeated players teleport to the inn. Once per playthrough.
"""

from evennia import create_object

from world.dungeons import register_dungeon
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Room generator
# ------------------------------------------------------------------ #

_CELLAR_DESC = (
    "A dank, low-ceilinged cellar beneath the inn. Broken barrels and "
    "rotting crates are piled against the walls. The floor is covered "
    "in gnaw marks, droppings, and scraps of chewed cloth. A chorus of "
    "high-pitched squeaking echoes from the shadows, and dozens of "
    "beady eyes glint in the darkness."
)


def generate_rat_cellar_room(instance, depth, coords):
    """
    Create the single rat cellar room and spawn all mobs.

    Args:
        instance: DungeonInstanceScript
        depth: Manhattan distance from origin (always 0)
        coords: (x, y) tuple (always (0, 0))
    Returns:
        DungeonRoom object
    """
    from typeclasses.actors.mobs.cellar_rat import CellarRat
    from typeclasses.actors.mobs.rat_king import RatKing
    from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

    room = create_object(DungeonRoom, key="Rat-Infested Cellar")
    room.db.desc = _CELLAR_DESC
    room.quest_tags = ["rat_cellar"]

    # Spawn 3 regular rats
    for _i in range(3):
        rat = create_object(
            CellarRat,
            key="a cellar rat",
            location=room,
            nohome=True,
        )
        rat.db.desc = (
            "A fat, mangy rat the size of a cat. Its fur is patchy "
            "and its teeth are bared in a permanent snarl."
        )
        rat.tags.add(instance.instance_key, category="dungeon_mob")
        rat.start_ai()

    # Spawn the Rat King (boss)
    king = create_object(
        RatKing,
        key="the Rat King",
        location=room,
        nohome=True,
    )
    king.db.desc = (
        "An enormous rat, easily the size of a large dog. Its matted "
        "grey fur is scarred and patchy, and its yellowed teeth are "
        "as long as daggers. A crude crown of twisted wire and bone "
        "sits atop its head. The other rats give it a wide berth."
    )
    king.tags.add(instance.instance_key, category="dungeon_mob")
    king.start_ai()

    return room


# ------------------------------------------------------------------ #
#  Template registration
# ------------------------------------------------------------------ #

RAT_CELLAR = DungeonTemplate(
    template_id="rat_cellar",
    name="The Rat Cellar",
    dungeon_type="instance",
    instance_mode="solo",
    boss_depth=99,  # irrelevant — no forward exits created
    max_unexplored_exits=0,
    max_new_exits_per_room=0,
    instance_lifetime_seconds=1800,  # 30 minutes
    room_generator=generate_rat_cellar_room,
    boss_generator=None,  # mobs spawned by room_generator
    room_typeclass="typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom",
    allow_combat=True,
    allow_pvp=False,
    allow_death=False,
    defeat_destination_key="The Harvest Moon",
    post_boss_linger_seconds=60,  # 1 min after Rat King dies
)

register_dungeon(RAT_CELLAR)

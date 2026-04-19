"""
Rat Cellar — 2-room instanced dungeon for the Harvest Moon cellar quest.

The game's first combat encounter. A solo instance with two rooms:
  Room 1 (depth 0): 2 cellar rats. Gated — must clear before proceeding.
  Room 2 (depth 1): The Rat King (boss). Quest completes on boss kill.

No-death: defeated players teleport to the inn. Once per playthrough.
"""

from evennia import create_object

from world.dungeons import register_dungeon
from world.dungeons.dungeon_template import DungeonTemplate


# ------------------------------------------------------------------ #
#  Room descriptions
# ------------------------------------------------------------------ #

_ROOM1_DESC = (
    "A dank, low-ceilinged cellar beneath the inn. Broken barrels and "
    "rotting crates are piled against the walls. The floor is covered "
    "in gnaw marks, droppings, and scraps of chewed cloth. A chorus of "
    "high-pitched squeaking echoes from the shadows, and dozens of "
    "beady eyes glint in the darkness."
)

_ROOM2_DESC = (
    "The cellar opens into a wider chamber, its walls slick with damp. "
    "Gnawed bones and scraps of food litter the floor around a nest of "
    "shredded cloth and straw. The squeaking here is louder, more "
    "aggressive — and something much larger than a rat shifts in the "
    "shadows."
)


# ------------------------------------------------------------------ #
#  Room generator
# ------------------------------------------------------------------ #

def generate_rat_cellar_room(instance, depth, coords):
    """
    Create a rat cellar room and spawn mobs based on depth.

    Depth 0: 2 cellar rats (encounter room — tagged not_clear).
    Depth 1+: Boss room (Rat King spawned via boss_generator).
    """
    from typeclasses.actors.mobs.cellar_rat import CellarRat
    from typeclasses.terrain.rooms.dungeon.dungeon_room import DungeonRoom

    if depth == 0:
        # First room — rat encounter
        room = create_object(DungeonRoom, key="Dank Cellar")
        room.db.desc = _ROOM1_DESC
        room.quest_tags = ["rat_cellar"]

        # Tag as not cleared — forward exits blocked until rats dead
        room.tags.add("not_clear", category="dungeon_room")

        # Spawn 2 cellar rats
        for _i in range(2):
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
    else:
        # Boss room
        room = create_object(DungeonRoom, key="Rat King's Lair")
        room.db.desc = _ROOM2_DESC

    return room


# ------------------------------------------------------------------ #
#  Boss generator
# ------------------------------------------------------------------ #

def generate_rat_king(instance, room):
    """Spawn the Rat King in the boss room."""
    from typeclasses.actors.mobs.rat_king import RatKing

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
        "sits atop its head."
    )
    king.tags.add(instance.instance_key, category="dungeon_mob")
    king.start_ai()
    return king


# ------------------------------------------------------------------ #
#  Template registration
# ------------------------------------------------------------------ #

RAT_CELLAR = DungeonTemplate(
    template_id="rat_cellar",
    name="The Rat Cellar",
    dungeon_type="instance",
    instance_mode="solo",
    boss_depth=1,
    max_unexplored_exits=1,
    max_new_exits_per_room=1,
    instance_lifetime_seconds=1800,  # 30 minutes (safety net)
    room_generator=generate_rat_cellar_room,
    boss_generator=generate_rat_king,
    room_typeclass="typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom",
    allow_combat=True,
    allow_pvp=False,
    allow_death=False,
    defeat_destination_key="The Harvest Moon",
    terrain_type="underground",
    always_lit=True,  # torchlit cellar
)

register_dungeon(RAT_CELLAR)

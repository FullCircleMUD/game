"""
DungeonTemplate — frozen dataclass defining dungeon configuration.

Each dungeon type (cave, sewer, forest, etc.) has a template that
controls depth, branching, lifetime, room/boss generation, and
instance mode.

Two dungeon types:
    "instance" — boss encounter at termination depth (dead-end).
    "passage"  — procedural corridor connecting two world rooms.

Three instance modes:
    "solo"   — one instance per player.
    "group"  — leader + followers share one instance.
    "shared" — one instance at a time per entrance, anyone can join.

Entry is via DungeonTriggerExit — a world exit that creates/joins a
dungeon instance when traversed. Players enter by walking, not by command.
"""

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class DungeonTemplate:
    """Immutable configuration for a dungeon type."""

    template_id: str
    """Unique identifier, e.g. 'cave_of_trials'."""

    name: str
    """Display name, e.g. 'The Cave of Trials'."""

    dungeon_type: str = "instance"
    """'instance' — boss at termination depth. 'passage' — connects two world rooms."""

    instance_mode: str = "solo"
    """'solo' — one per player. 'group' — leader + followers. 'shared' — anyone joins."""

    boss_depth: int = 5
    """Manhattan distance from origin at which the dungeon terminates.
    For 'instance' type: boss room spawns here.
    For 'passage' type: exit to destination world room created here."""

    max_unexplored_exits: int = 2
    """Exit budget — max unvisited exits that can exist at once."""

    max_new_exits_per_room: int = 2
    """Max new forward exits created per room (controls branching)."""

    instance_lifetime_seconds: int = 7200
    """How long the instance stays alive (default 7200 = 2 hours)."""

    room_generator: Callable = None
    """func(instance, depth, coords) → DungeonRoom object."""

    boss_generator: Optional[Callable] = None
    """func(instance, room) → boss NPC object. None for passage dungeons."""

    room_typeclass: str = "typeclasses.terrain.rooms.dungeon.dungeon_room.DungeonRoom"
    """Dotted path to the DungeonRoom typeclass."""

    allow_combat: bool = True
    """Whether combat is allowed in dungeon rooms."""

    allow_pvp: bool = False
    """Whether PvP is allowed in dungeon rooms."""

    allow_death: bool = False
    """If False, defeated players teleport to entrance (defeat mode)."""

    defeat_destination_key: Optional[str] = None
    """Room key for defeat respawn. If None, uses the dungeon entrance."""

    post_boss_linger_seconds: int = 300
    """Seconds after boss defeated before instance collapses (default 5 min)."""

    empty_collapse_delay: int = 0
    """Seconds to keep a shared instance alive after all players leave.
    0 = collapse on next tick (default). Useful for shared mode."""

    terrain_type: str = "dungeon"
    """Terrain type tag for generated rooms (e.g. 'dungeon', 'forest',
    'underground'). Applied via room.set_terrain() during room creation.
    Controls lighting, weather exposure, and forage availability."""

    always_lit: bool = False
    """If True, dungeon rooms are permanently lit (no darkness checks)."""

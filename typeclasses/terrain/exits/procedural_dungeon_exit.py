"""
ProceduralDungeonExit — simple dungeon entry exit.

Always enters a procedural dungeon on traversal. No conditional routing.
Composes ProceduralDungeonMixin with ExitVerticalAware for direction
system support.

Use this for unconditional dungeon entries (deep woods passages, cave
of trials, etc.). For quest-gated entries with a fallback room, use
ConditionalDungeonExit instead.

See design/EXIT_ARCHITECTURE.md and design/PROCEDURAL_DUNGEONS.md.
"""

from typeclasses.mixins.procedural_dungeon import ProceduralDungeonMixin
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware


class ProceduralDungeonExit(ProceduralDungeonMixin, ExitVerticalAware):
    """
    World exit that always creates/joins a dungeon instance when traversed.

    Builder usage:
        trigger = create_object(
            ProceduralDungeonExit,
            key="Deep Woods",
            location=entry_room,
            destination=entry_room,  # self-referential
        )
        trigger.set_direction("north")
        trigger.dungeon_template_id = "deep_woods_passage"
        trigger.dungeon_destination_room_id = clearing_room.id  # passages
    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """Enter the procedural dungeon. Does not call super()."""
        if getattr(traversing_object, "is_pet", False):
            if self.location:
                self.location.msg_contents(
                    f"An invisible barrier stops {traversing_object.key} "
                    f"from entering."
                )
            return
        self.enter_dungeon(traversing_object)

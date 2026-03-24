"""
DungeonExit — an exit inside a procedural dungeon that lazily creates
the destination room when first traversed.

On creation, a DungeonExit's destination is set to its own location
(points back to itself). When a player traverses it, `at_traverse`
detects this and asks the DungeonInstanceScript to generate the
actual destination room. The exit is then permanently linked.

Forward exits are gated by the `not_clear` tag on the source room,
so players must clear encounters before proceeding.

Inherits from ExitVerticalAware to gain direction aliases, height
checks, and proper exit display formatting.
"""

from evennia import AttributeProperty

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware


class DungeonExit(ExitVerticalAware):
    """Exit in a procedural dungeon with lazy room creation."""

    dungeon_instance_id = AttributeProperty(None)
    is_return_exit = AttributeProperty(False)

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Called when someone tries to traverse this exit.

        If the exit still points back to its own location (lazy placeholder),
        ask the dungeon instance script to generate the real destination.
        Forward exits are blocked while the source room has the not_clear tag.
        """
        # Gate forward exits on room clearance
        if not self.is_return_exit:
            if self.location.tags.has("not_clear", category="dungeon_room"):
                traversing_object.msg("|rThe path forward is blocked!|n")
                return

        # Lazy creation: exit points back to its own location
        if target_location == self.location:
            instance_script = self._get_instance_script()
            if not instance_script:
                traversing_object.msg("The passage has collapsed.")
                return
            new_room = instance_script.create_room_from_exit(self)
            if not new_room:
                traversing_object.msg("The passage has collapsed.")
                return
            self.destination = new_room
            target_location = new_room

        super().at_traverse(traversing_object, target_location, **kwargs)

    def _get_instance_script(self):
        """Look up the DungeonInstanceScript by ID."""
        from evennia import ScriptDB

        if not self.dungeon_instance_id:
            return None
        try:
            return ScriptDB.objects.get(id=self.dungeon_instance_id)
        except ScriptDB.DoesNotExist:
            return None

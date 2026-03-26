"""
DungeonPassageExit — exit at the endpoints of a procedural dungeon.

Used in two places:
    1. Room (0,0) → entrance world room  (walk back out)
    2. Final room → destination world room  (emerge at the other end)

Traversing this exit removes the character from the dungeon instance
(clears their dungeon tag). Followers in the same instance are also
untagged, since follower cascade via at_post_move bypasses exit
at_traverse and wouldn't otherwise clean up their tags.

Inherits from ExitVerticalAware for direction system and vertical checks.
"""

from evennia import AttributeProperty

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware


class DungeonPassageExit(ExitVerticalAware):
    """Exit at a passage dungeon boundary — removes dungeon tag on traverse."""

    dungeon_instance_id = AttributeProperty(None)

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """Remove character (and followers) from instance, then traverse."""
        instance = self._get_instance_script()
        if instance:
            instance.remove_character(traversing_object)
            # Untag followers still in this dungeon instance — they'll be
            # moved to target_location by the normal follower cascade, but
            # that cascade bypasses exit at_traverse so we must untag here.
            if hasattr(traversing_object, "get_followers"):
                for f in traversing_object.get_followers(same_room=False):
                    tag = f.tags.get(category="dungeon_character")
                    if tag and tag == instance.instance_key:
                        instance.remove_character(f)
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

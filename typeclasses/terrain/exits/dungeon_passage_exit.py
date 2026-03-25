"""
DungeonPassageExit — exit at the endpoints of a procedural passage dungeon.

Used in two places:
    1. Room (0,0) → entrance world room  (walk back out)
    2. Final room → destination world room  (emerge at the other end)

Traversing this exit removes the character from the dungeon instance
(clears their dungeon tag). Followers in the same instance are also
untagged, since follower cascade via at_post_move bypasses exit
at_traverse and wouldn't otherwise clean up their tags.

Inherits from ExitBase for proper exit descriptions. Direction support
is provided directly for consistent display in the auto-exit line.
"""

from evennia import AttributeProperty

from typeclasses.terrain.exits.exit_base import ExitBase


class DungeonPassageExit(ExitBase):
    """Exit at a passage dungeon boundary — removes dungeon tag on traverse."""

    # ── Direction system (shared with ExitVerticalAware) ──────────────
    DIRECTION_ALIASES = {
        "north": ["n", "north"],
        "south": ["s", "south"],
        "east": ["e", "east"],
        "west": ["w", "west"],
        "northeast": ["ne", "northeast"],
        "northwest": ["nw", "northwest"],
        "southeast": ["se", "southeast"],
        "southwest": ["sw", "southwest"],
        "up": ["u", "up"],
        "down": ["d", "down"],
        "in": ["in"],
        "out": ["out"],
    }

    direction = AttributeProperty("default")

    def set_direction(self, direction):
        """
        Set the compass direction and auto-add direction aliases.

        Args:
            direction (str): A key from DIRECTION_ALIASES (e.g. "north").
        """
        self.direction = direction
        aliases = self.DIRECTION_ALIASES.get(direction, [])
        current = set(self.aliases.all())
        for alias in aliases:
            if alias not in current:
                self.aliases.add(alias)

    def get_display_name(self, looker=None, **kwargs):
        """
        Format the exit for room display.

        If direction is set, returns "direction: description".
        Otherwise falls back to desc or key.
        """
        desc = self.db.desc or self.key
        if self.direction in self.DIRECTION_ALIASES:
            return f"{self.direction}: {desc}"
        return desc

    # ── Dungeon attributes ────────────────────────────────────────────

    dungeon_instance_id = AttributeProperty(None)

    # ── Traversal ─────────────────────────────────────────────────────

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

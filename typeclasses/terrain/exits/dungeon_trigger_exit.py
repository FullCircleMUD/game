"""
DungeonTriggerExit — a world exit that triggers dungeon entry on traversal.

Placed by builders as a normal exit; when a player walks through it, a
dungeon instance is created (or joined) and the player is moved into the
first dungeon room. This is the sole entry mechanism for procedural
dungeons — players enter by walking, not by typing a command.

Supports optional quest gating via ``quest_key`` and ``fallback_destination_id``.
When a quest_key is set:
  - Quest active (accepted, not completed) → creates dungeon instance.
  - Quest not accepted or already completed → routes to fallback destination.

Uses a self-referential destination (exit points back to its own location),
the same pattern used by DungeonExit for lazy room creation. The real
movement is handled entirely in at_traverse.

Inherits from ExitBase (not ExitVerticalAware) for proper exit descriptions.
Direction support is provided directly — ExitVerticalAware's vertical checks
are not needed since this exit completely overrides at_traverse.
"""

from evennia import AttributeProperty
from evennia.utils.create import create_script

from typeclasses.terrain.exits.exit_base import ExitBase
from world.dungeons import get_dungeon_template


class DungeonTriggerExit(ExitBase):
    """
    World exit that creates/joins a dungeon instance when traversed.

    Builder usage:
        trigger = create_object(
            DungeonTriggerExit,
            key="a small wooden door",
            location=world_room,
            destination=world_room,  # self-referential
        )
        trigger.set_direction("south")
        trigger.dungeon_template_id = "cave_of_trials"
        trigger.dungeon_destination_room_id = other_world_room.id  # passages

        # Optional quest gating:
        trigger.quest_key = "rat_cellar"
        trigger.fallback_destination_id = permanent_cellar.id
    """

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

    dungeon_template_id = AttributeProperty(None)
    dungeon_destination_room_id = AttributeProperty(None)  # passage endpoint

    # ── Quest gating (optional) ───────────────────────────────────────

    quest_key = AttributeProperty(None)
    fallback_destination_id = AttributeProperty(None)

    # ── Traversal ─────────────────────────────────────────────────────

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Intercept traversal to create/join a dungeon instance.

        If quest_key is set, routes based on quest state:
          - Quest active → dungeon instance
          - Quest not accepted or completed → fallback destination
        """
        # Quest gating — route to fallback if quest not active
        if self.quest_key and hasattr(traversing_object, "quests"):
            quest_active = (
                traversing_object.quests.has(self.quest_key)
                and not traversing_object.quests.is_completed(self.quest_key)
            )
            if not quest_active:
                self._move_to_fallback(traversing_object)
                return

        # Standard dungeon entry
        template_id = self.dungeon_template_id
        if not template_id:
            traversing_object.msg("This passage leads nowhere.")
            return

        try:
            template = get_dungeon_template(template_id)
        except KeyError:
            traversing_object.msg("This passage is not configured properly.")
            return

        # Already in a dungeon — don't stack instances
        existing_tag = traversing_object.tags.get(category="dungeon_character")
        if existing_tag:
            traversing_object.msg("You are already in a dungeon.")
            return

        # Collect characters based on instance mode
        characters = self._collect_characters(traversing_object, template)
        if characters is None:
            return  # validation failed, message already sent

        # Check none of these characters already have a dungeon tag
        for char in characters:
            tag = char.tags.get(category="dungeon_character")
            if tag:
                traversing_object.msg(
                    f"{char.key} is already in another dungeon instance."
                )
                return

        # Resolve or create the instance
        instance = self._resolve_instance(traversing_object, template)
        if not instance:
            return

        # New instance — start it with the collected characters
        if not instance.db.xy_grid:
            self._announce_entry(traversing_object, characters, template)
            instance.start_dungeon(characters)
        else:
            # Existing shared instance — add characters and move them in
            self._join_existing(characters, instance, template)

        # Do NOT call super().at_traverse() — characters are already moved
        # by start_dungeon or _join_existing.

    # ── Quest fallback ────────────────────────────────────────────────

    def _move_to_fallback(self, traversing_object):
        """Send the traverser to the fallback (non-dungeon) destination."""
        from evennia import ObjectDB

        if not self.fallback_destination_id:
            traversing_object.msg("The passage seems blocked.")
            return
        try:
            dest = ObjectDB.objects.get(id=self.fallback_destination_id)
            traversing_object.move_to(dest)
        except ObjectDB.DoesNotExist:
            traversing_object.msg("The passage seems blocked.")

    # ── Character collection ──────────────────────────────────────────

    def _collect_characters(self, traversing_object, template):
        """
        Collect characters to enter based on instance_mode.

        Returns list of characters, or None if validation fails.
        """
        if template.instance_mode == "group":
            leader = traversing_object.get_group_leader()
            if leader != traversing_object and leader.location == self.location:
                traversing_object.msg(
                    f"Only your group leader ({leader.key}) can enter."
                )
                return None
            characters = [traversing_object]
            followers = traversing_object.get_followers(same_room=True)
            characters.extend(followers)
            return characters
        else:
            # Solo and shared — single character
            return [traversing_object]

    # ── Instance resolution ───────────────────────────────────────────

    def _resolve_instance(self, traversing_object, template):
        """Find existing or create new instance based on instance_mode."""
        from evennia import ScriptDB

        template_id = template.template_id

        # Determine instance key
        if template.instance_mode == "shared":
            instance_key = f"{template_id}_shared_{self.id}"
            # Check for existing shared instance
            try:
                existing = ScriptDB.objects.get(db_key=instance_key)
                if existing.state == "active":
                    return existing
            except ScriptDB.DoesNotExist:
                pass
        elif template.instance_mode == "group":
            leader = traversing_object.get_group_leader()
            instance_key = f"{template_id}_{leader.id}"
        else:
            # Solo
            instance_key = f"{template_id}_{traversing_object.id}"

        # Create new instance
        instance = create_script(
            "typeclasses.scripts.dungeon_instance.DungeonInstanceScript",
            key=instance_key,
            autostart=False,
        )
        instance.template_id = template_id
        instance.instance_key = instance_key
        instance.entrance_room_id = self.location.id
        instance.entrance_direction = self.direction if self.direction != "default" else None

        # For passages, set the destination room
        if self.dungeon_destination_room_id:
            instance.destination_room_id = self.dungeon_destination_room_id

        instance.start()
        return instance

    # ── Shared instance join ──────────────────────────────────────────

    def _join_existing(self, characters, instance, template):
        """Add characters to an existing shared instance."""
        from evennia import ObjectDB

        grid = dict(instance.db.xy_grid or {})
        first_room_id = grid.get((0, 0))
        first_room = None
        if first_room_id:
            try:
                first_room = ObjectDB.objects.get(id=first_room_id)
            except ObjectDB.DoesNotExist:
                pass

        for char in characters:
            instance.add_character(char)
            if first_room:
                char.move_to(first_room, quiet=True, move_type="teleport")

    # ── Entry announcement ────────────────────────────────────────────

    def _announce_entry(self, caller, characters, template):
        """Announce dungeon entry to the source room."""
        room = self.location
        if len(characters) > 1:
            names = ", ".join(c.key for c in characters)
            room.msg_contents(
                f"|y{names} enter {template.name}!|n",
                from_obj=caller,
            )
        else:
            room.msg_contents(
                f"|y{caller.key} enters {template.name}!|n",
                from_obj=caller,
                exclude=[caller],
            )

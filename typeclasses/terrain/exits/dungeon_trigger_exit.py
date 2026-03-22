"""
DungeonTriggerExit — a world exit that triggers dungeon entry on traversal.

Movement-triggered alternative to DungeonEntranceRoom (command-triggered).
Placed by builders as a normal exit; when a player walks through it, a
dungeon instance is created (or joined) and the player is moved into the
first dungeon room.

The entry trigger is determined by builder placement, not by the template.
The same template can be used with either DungeonEntranceRoom (command)
or DungeonTriggerExit (movement). This allows builders to choose the
experience per entrance without changing the dungeon definition.

Uses a self-referential destination (exit points back to its own location),
the same pattern used by DungeonExit for lazy room creation. The real
movement is handled entirely in at_traverse.
"""

from evennia import AttributeProperty, DefaultExit
from evennia.utils.create import create_script

from world.dungeons import get_dungeon_template


class DungeonTriggerExit(DefaultExit):
    """
    World exit that creates/joins a dungeon instance when traversed.

    Builder usage:
        trigger = create_object(
            DungeonTriggerExit,
            key="dark cave",
            location=world_room,
            destination=world_room,  # self-referential
        )
        trigger.dungeon_template_id = "cave_of_trials"
        trigger.dungeon_destination_room_id = other_world_room.id  # passages
    """

    dungeon_template_id = AttributeProperty(None)
    dungeon_destination_room_id = AttributeProperty(None)  # passage endpoint

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """Intercept traversal to create/join a dungeon instance."""
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

        # For passages, set the destination room
        if self.dungeon_destination_room_id:
            instance.destination_room_id = self.dungeon_destination_room_id

        instance.start()
        return instance

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
                char.msg(f"|y{template.name}|n")
                char.msg(first_room.db.desc or "You enter the dungeon.")

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

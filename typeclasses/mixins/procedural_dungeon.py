"""
ProceduralDungeonMixin — adds dungeon instance creation capability to any exit.

Provides ``enter_dungeon(traversing_object)`` as a utility method. Does NOT
override ``at_traverse`` — the host class decides when to call it.

This mixin can be composed with any exit type:
    ProceduralDungeonExit(ProceduralDungeonMixin, ExitVerticalAware)
    ConditionalDungeonExit(ProceduralDungeonMixin, ConditionalRoutingExit)
    DungeonDoor(ProceduralDungeonMixin, ExitDoor)

See design/EXIT_ARCHITECTURE.md and design/PROCEDURAL_DUNGEONS.md.
"""

from evennia import AttributeProperty
from evennia.utils.create import create_script

from world.dungeons import get_dungeon_template


class ProceduralDungeonMixin:
    """
    Mixin that provides procedural dungeon entry capability to any exit.

    Attributes:
        dungeon_template_id: Template ID to instantiate (e.g. "rat_cellar").
        dungeon_destination_room_id: For passage dungeons, the destination
            world room ID.
    """

    dungeon_template_id = AttributeProperty(None)
    dungeon_destination_room_id = AttributeProperty(None)

    def enter_dungeon(self, traversing_object):
        """
        Create or join a procedural dungeon instance.

        Handles template lookup, dungeon tag checks, character collection,
        instance resolution, and entry. Characters are moved into the
        dungeon's first room.

        Three-way entry logic:
        1. Already physically in a dungeon (`dungeon_character` set) → reject.
        2. Has `dungeon_pending` matching this template → redirect into the
           existing instance alone (followers/pets stay outside).
        3. Otherwise → normal new-instance flow with full follower collection.

        Args:
            traversing_object: The character entering the dungeon.

        Returns:
            True if the character was moved into a dungeon.
            False if entry failed (error messages already sent).
        """
        template_id = self.dungeon_template_id
        if not template_id:
            traversing_object.msg("This passage leads nowhere.")
            return False

        try:
            template = get_dungeon_template(template_id)
        except KeyError:
            traversing_object.msg("This passage is not configured properly.")
            return False

        # 1. Already in a dungeon — don't stack instances
        if traversing_object.tags.get(category="dungeon_character"):
            traversing_object.msg("You are already in a dungeon.")
            return False

        # 2. Pending recovery for this template — redirect alone
        if self._try_pending_recovery_redirect(traversing_object, template):
            return True

        # 3. Normal new-instance flow — collect followers/pets and validate
        characters = self._collect_dungeon_characters(
            traversing_object, template
        )
        if characters is None:
            return False  # validation failed, message already sent

        # Check none of these characters already have a dungeon tag
        for char in characters:
            tag = char.tags.get(category="dungeon_character")
            if tag:
                traversing_object.msg(
                    f"{char.key} is already in another dungeon instance."
                )
                return False

        # Resolve or create the instance
        instance = self._resolve_dungeon_instance(
            traversing_object, template
        )
        if not instance:
            return False

        # New instance — start it with the collected characters
        if not instance.db.xy_grid:
            self._announce_dungeon_entry(
                traversing_object, characters, template
            )
            instance.start_dungeon(characters)
        else:
            # Existing shared instance — add characters and move them in
            self._join_existing_dungeon(characters, instance, template)

        return True

    def _try_pending_recovery_redirect(self, traversing_object, template):
        """If traverser has a `dungeon_pending` tag matching THIS template,
        redirect them into the existing instance — alone, no followers.

        Stale pending tags (instance gone, instance not active, or instance
        in a corrupt state) are scrubbed silently and the method returns
        False so the caller can proceed with the normal new-instance flow.

        Returns:
            True if the player was redirected into an existing instance.
            False if no matching pending tag found, or all matches were stale.
        """
        pending_keys = traversing_object.tags.get(
            category="dungeon_pending", return_list=True
        )
        if not pending_keys:
            return False

        from evennia import ObjectDB, ScriptDB

        for instance_key in pending_keys:
            try:
                instance = ScriptDB.objects.get(db_key=instance_key)
            except ScriptDB.DoesNotExist:
                # Stale — scrub and keep looking
                traversing_object.tags.remove(
                    instance_key, category="dungeon_pending"
                )
                continue

            if instance.state != "active":
                # Collapsing or done — also stale
                traversing_object.tags.remove(
                    instance_key, category="dungeon_pending"
                )
                continue

            if instance.template_id != template.template_id:
                # Pending tag exists but for a different template — leave the
                # tag alone, fall through to normal entry for THIS template.
                continue

            # Live, matching instance — resolve room (0,0) and redirect alone
            grid = dict(instance.db.xy_grid or {})
            first_room_id = grid.get((0, 0))
            first_room = None
            if first_room_id:
                try:
                    first_room = ObjectDB.objects.get(id=first_room_id)
                except ObjectDB.DoesNotExist:
                    pass
            if not first_room:
                # Instance corrupt — scrub and keep looking
                traversing_object.tags.remove(
                    instance_key, category="dungeon_pending"
                )
                continue

            # add_character tags with dungeon_character; pending tag is
            # retained until corpse is fully looted or decays.
            instance.add_character(traversing_object)
            traversing_object.move_to(
                first_room, quiet=True, move_type="teleport"
            )
            traversing_object.msg(
                "|yYou return to recover your remains.|n"
            )
            return True

        return False

    # ── Character collection ──────────────────────────────────────────

    def _collect_dungeon_characters(self, traversing_object, template):
        """
        Collect characters to enter based on instance_mode.

        Returns list of characters, or None if validation fails.
        """
        if template.instance_mode == "solo":
            # Solo — no followers or pets allowed
            followers = traversing_object.get_followers(same_room=True)
            if followers:
                traversing_object.msg(
                    "You can only enter here alone, ungroup and leave "
                    "your pets outside."
                )
                return None
            return [traversing_object]

        elif template.instance_mode == "group":
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
            # Shared — collect followers (including pets) like group mode
            characters = [traversing_object]
            followers = traversing_object.get_followers(same_room=True)
            characters.extend(followers)
            return characters

    # ── Instance resolution ───────────────────────────────────────────

    def _resolve_dungeon_instance(self, traversing_object, template):
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
        instance.entrance_direction = (
            self.direction if getattr(self, "direction", "default") != "default"
            else None
        )

        # For passages, set the destination room
        if self.dungeon_destination_room_id:
            instance.destination_room_id = self.dungeon_destination_room_id

        instance.start()
        return instance

    # ── Shared instance join ──────────────────────────────────────────

    def _join_existing_dungeon(self, characters, instance, template):
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

    def _announce_dungeon_entry(self, caller, characters, template):
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

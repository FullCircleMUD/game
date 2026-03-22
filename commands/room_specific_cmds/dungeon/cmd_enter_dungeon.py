"""
CmdEnterDungeon — enter a procedural dungeon instance.

Available in DungeonEntranceRoom (command-triggered entry).
Creates a new dungeon instance (or re-enters an existing one)
and teleports the player (and group in 'group' instance mode)
into the first dungeon room.

For movement-triggered entry, see DungeonTriggerExit instead.
The entry trigger is determined by builder placement, not by the template.
"""

from evennia import Command
from evennia.utils.create import create_script

from world.dungeons import get_dungeon_template


class CmdEnterDungeon(Command):
    """
    Enter the dungeon.

    Usage:
        enter dungeon
        enter

    In 'group' mode, the leader and all followers in the room
    enter together. In 'solo' mode, only you enter.
    In 'shared' mode, you join the existing instance or start a new one.

    If you already have an active instance, you will be returned to it.
    """

    key = "enter"
    aliases = ["enter dungeon"]
    locks = "cmd:all()"
    help_category = "Dungeon"

    def func(self):
        caller = self.caller
        room = caller.location

        template_id = getattr(room, "dungeon_template_id", None)
        if not template_id:
            caller.msg("There is no dungeon to enter here.")
            return

        try:
            template = get_dungeon_template(template_id)
        except KeyError:
            caller.msg("This dungeon is not configured properly.")
            return

        # Check if caller already has an active instance for this template
        existing_tag = caller.tags.get(category="dungeon_character")
        if existing_tag:
            # Try to find the existing instance
            from typeclasses.scripts.dungeon_instance import DungeonInstanceScript
            from evennia import ScriptDB

            instances = ScriptDB.objects.filter(
                db_typeclass_path__contains="dungeon_instance",
                db_key__startswith=template_id,
            )
            for inst in instances:
                if inst.state == "active" and existing_tag == inst.instance_key:
                    # Re-enter existing instance — find their last room
                    rooms = list(
                        inst.db.xy_grid.values()
                    ) if inst.db.xy_grid else []
                    if rooms:
                        from evennia import ObjectDB

                        try:
                            last_room = ObjectDB.objects.get(id=rooms[-1])
                            caller.msg("You re-enter the dungeon...")
                            caller.move_to(last_room, quiet=True, move_type="teleport")
                            return
                        except ObjectDB.DoesNotExist:
                            pass
            # Instance gone — clean up stale tag
            caller.tags.remove(existing_tag, category="dungeon_character")

        # Shared mode — check for existing shared instance to join
        if template.instance_mode == "shared":
            instance_key = f"{template_id}_shared_{room.id}"
            joined = self._try_join_shared(caller, template, instance_key)
            if joined:
                return
        else:
            instance_key = f"{template_id}_{caller.id}"

        # Collect characters to enter
        if template.instance_mode == "group":
            # Leader + followers in the same room
            leader = caller.get_group_leader()
            if leader != caller and leader.location == room:
                # Caller is a follower, not the leader — only leader can enter
                caller.msg(
                    f"Only your group leader ({leader.key}) can enter the dungeon."
                )
                return
            # Collect followers in the room
            characters = [caller]
            followers = caller.get_followers(same_room=True)
            characters.extend(followers)
        else:
            # Solo or shared — single character
            characters = [caller]

        # Check none of these characters already have a dungeon tag
        for char in characters:
            tag = char.tags.get(category="dungeon_character")
            if tag:
                caller.msg(
                    f"{char.key} is already in another dungeon instance."
                )
                return

        # Create the instance
        instance = create_script(
            "typeclasses.scripts.dungeon_instance.DungeonInstanceScript",
            key=instance_key,
            autostart=False,
        )
        instance.template_id = template_id
        instance.instance_key = instance_key
        instance.entrance_room_id = room.id

        # For passages, set the destination room
        dest_id = getattr(room, "dungeon_destination_room_id", None)
        if dest_id:
            instance.destination_room_id = dest_id

        instance.start()

        # Announce and start
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

        instance.start_dungeon(characters)

    def _try_join_shared(self, caller, template, instance_key):
        """Try to join an existing shared instance. Returns True if joined."""
        from evennia import ScriptDB, ObjectDB

        try:
            existing = ScriptDB.objects.get(db_key=instance_key)
        except ScriptDB.DoesNotExist:
            return False

        if existing.state != "active":
            return False

        existing.add_character(caller)
        grid = dict(existing.db.xy_grid or {})
        if (0, 0) in grid:
            try:
                first_room = ObjectDB.objects.get(id=grid[(0, 0)])
                caller.msg(f"|y{template.name}|n")
                caller.move_to(first_room, quiet=True, move_type="teleport")
                caller.msg(first_room.db.desc or "You enter the dungeon.")
                return True
            except ObjectDB.DoesNotExist:
                pass
        return False

"""
CmdExitDungeon — leave a dungeon instance.

Available inside DungeonRooms. Teleports the character back to the
dungeon entrance and removes their instance tag. If all characters
leave, the instance collapses on the next tick.
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdExitDungeon(FCMCommandMixin, Command):
    """
    Leave the dungeon and return to the entrance.

    Usage:
        exit dungeon
        leave dungeon
        flee dungeon
    """

    key = "exit dungeon"
    aliases = ["leave dungeon", "flee dungeon"]
    locks = "cmd:all()"
    help_category = "Dungeon"

    def func(self):
        caller = self.caller

        # Find the instance this character belongs to
        instance_tag = caller.tags.get(category="dungeon_character")
        if not instance_tag:
            caller.msg("You are not in a dungeon.")
            return

        from evennia import ScriptDB

        try:
            instance = ScriptDB.objects.get(db_key=instance_tag)
        except ScriptDB.DoesNotExist:
            # Stale tag — clean up
            caller.tags.remove(instance_tag, category="dungeon_character")
            caller.msg("Your dungeon instance no longer exists.")
            return

        entrance = instance.entrance_room
        if not entrance:
            caller.msg("The dungeon entrance has been lost.")
            return

        # Remove from instance and teleport out
        instance.remove_character(caller)
        caller.msg("|yYou flee the dungeon!|n")
        caller.location.msg_contents(
            f"$You() $conj(flee) the dungeon!",
            from_obj=caller,
            exclude=[caller],
        )
        caller.move_to(entrance, quiet=True, move_type="teleport")
        caller.msg(entrance.db.desc or "You emerge from the dungeon.")

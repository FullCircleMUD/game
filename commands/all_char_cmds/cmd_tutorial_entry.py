"""
Tutorial entry and exit commands.

CmdEnterTutorial — start or re-enter the tutorial from anywhere (``tutorial``).
CmdLeaveTutorial — leave the tutorial mid-way (no reward).
"""

from evennia import Command

from commands.command import FCMCommandMixin
from evennia import ScriptDB


class CmdEnterTutorial(FCMCommandMixin, Command):
    """
    Enter or re-enter the tutorial.

    Usage:
        tutorial

    Teleports you to the Tutorial Hub where you can choose which
    tutorial to start. Available at any time (except during combat
    or purgatory).
    """

    key = "tutorial"
    aliases = ["tute"]
    locks = "cmd:all()"
    help_category = "Tutorial"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        # Check not in purgatory
        if getattr(caller, "in_purgatory", False):
            caller.msg("You can't access the tutorial while in purgatory.")
            return

        # Check not in combat
        if caller.scripts.get("combat_handler"):
            caller.msg("You can't access the tutorial while in combat.")
            return

        # Check not already in a tutorial instance
        tutorial_tags = caller.tags.get(category="tutorial_character", return_list=True)
        if tutorial_tags:
            caller.msg("You are already in a tutorial. Use |wleave tutorial|n to exit first.")
            return

        from world.tutorial.tutorial_hub_builder import build_tutorial_hub, get_tutorial_hub

        # Already in the hub? Just show the room.
        hub = get_tutorial_hub()
        if hub and caller.location == hub:
            caller.msg("You are already in the Tutorial Hub. Choose a direction to begin.")
            return

        hub = build_tutorial_hub()

        # Store current location so south exit can return here
        if caller.location:
            caller.db.pre_tutorial_location_id = caller.location.id

        caller.move_to(hub, quiet=True, move_type="teleport")
        caller.msg("|cYou are transported to the Tutorial Hub.|n")


class CmdLeaveTutorial(FCMCommandMixin, Command):
    """
    Leave the tutorial and return to the Tutorial Hub.

    Usage:
        leave tutorial
        exit tutorial

    Abandons the current tutorial. Tutorial items will be removed.
    You can restart the tutorial later from the hub.
    """

    key = "leave tutorial"
    aliases = ["exit tutorial"]
    locks = "cmd:all()"
    help_category = "Tutorial"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        # Find the tutorial instance for this character
        tutorial_tags = caller.tags.get(category="tutorial_character", return_list=True)
        if not tutorial_tags:
            # Check if they're in the Tutorial Hub — guide them to the exit
            from world.tutorial.tutorial_hub_builder import get_tutorial_hub
            hub = get_tutorial_hub()
            if hub and caller.location == hub:
                caller.msg(
                    "You are in the Tutorial Hub. To leave the tutorial, "
                    "type |wsouth|n."
                )
            else:
                caller.msg("You are not in a tutorial.")
            return

        instance_key = tutorial_tags[0] if tutorial_tags else None
        if not instance_key:
            caller.msg("You are not in a tutorial.")
            return

        # Find the script
        try:
            scripts = ScriptDB.objects.filter(db_key=instance_key)
            if scripts.exists():
                script = scripts.first()
                if hasattr(script, "collapse_instance"):
                    caller.msg("|yLeaving tutorial...|n")
                    script.collapse_instance(give_reward=False)
                    return
        except Exception:
            pass

        # Fallback — just remove the tag and go to hub
        caller.tags.remove(instance_key, category="tutorial_character")
        from world.tutorial.tutorial_hub_builder import build_tutorial_hub
        hub = build_tutorial_hub()
        caller.move_to(hub, quiet=True, move_type="teleport")
        caller.msg("|cYou return to the Tutorial Hub.|n")

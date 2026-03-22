"""
Custom exits for the Tutorial Hub.

ExitTutorialStart — east/north/west exits that start a tutorial instance.
ExitTutorialReturn — south exit that returns the player to their
    pre-tutorial location (or The Harvest Moon for new characters).
"""

from evennia import ObjectDB
from .exit_vertical_aware import ExitVerticalAware


class ExitTutorialStart(ExitVerticalAware):
    """
    An exit that starts a tutorial instance when traversed.

    Attributes:
        tutorial_num (int): Which tutorial to start (1, 2, 3).
    """

    def at_traverse(self, traversing_object, destination, **kwargs):
        tutorial_num = self.db.tutorial_num or 0

        if tutorial_num not in (1, 2, 3):
            traversing_object.msg("|xThis tutorial is not available.|n")
            return

        # Check not already in a tutorial
        tutorial_tags = traversing_object.tags.get(
            category="tutorial_character", return_list=True
        )
        if tutorial_tags:
            traversing_object.msg(
                "You are already in a tutorial. "
                "Use |wleave tutorial|n to exit first."
            )
            return

        # Start the selected tutorial
        from world.tutorial.tutorial_hub_builder import get_tutorial_hub
        from evennia.utils.create import create_script
        from typeclasses.scripts.tutorial_instance import TutorialInstanceScript

        hub = get_tutorial_hub()
        if not hub:
            traversing_object.msg("|rTutorial Hub not found.|n")
            return

        script = create_script(
            TutorialInstanceScript,
            key=f"tutorial_{tutorial_num}_{traversing_object.id}",
            autostart=False,
        )
        script.instance_key = script.key
        script.hub_room_id = hub.id
        script.start()

        script.start_tutorial(traversing_object, chunk_num=tutorial_num)


class ExitTutorialReturn(ExitVerticalAware):
    """
    South exit from the Tutorial Hub — returns the player to their
    pre-tutorial location, or The Harvest Moon for new characters.
    """

    def at_traverse(self, traversing_object, destination, **kwargs):
        # Check if they have a stored location
        prev_id = traversing_object.db.pre_tutorial_location_id
        target = None

        if prev_id:
            try:
                target = ObjectDB.objects.get(id=prev_id)
            except ObjectDB.DoesNotExist:
                pass

        if not target:
            # New character or stale location — go to Harvest Moon
            target = ObjectDB.objects.filter(
                db_key="The Harvest Moon"
            ).first()

        if not target:
            # Last resort — Limbo
            try:
                target = ObjectDB.objects.get(id=2)
            except ObjectDB.DoesNotExist:
                traversing_object.msg("|rCould not find a destination.|n")
                return

        # Clean up any lingering tutorial state
        tutorial_tags = traversing_object.tags.get(
            category="tutorial_character", return_list=True
        )
        if tutorial_tags:
            from evennia import ScriptDB
            for tag in tutorial_tags:
                # Collapse the instance if it still exists
                scripts = ScriptDB.objects.filter(db_key=tag)
                for script in scripts:
                    if hasattr(script, "collapse_instance"):
                        script.collapse_instance(give_reward=False)
                # Remove tag in case collapse didn't (e.g. script already gone)
                traversing_object.tags.remove(tag, category="tutorial_character")
            # Clean up any leftover tutorial items
            for item in list(traversing_object.contents):
                if getattr(item.db, "tutorial_item", False):
                    item.delete()

        traversing_object.move_to(target, quiet=True, move_type="teleport")
        traversing_object.msg("|cYou leave the Tutorial Hub.|n")
        traversing_object.msg(
            "You can always return with |wtutorial|n."
        )
        # Clean up stored location
        traversing_object.db.pre_tutorial_location_id = None

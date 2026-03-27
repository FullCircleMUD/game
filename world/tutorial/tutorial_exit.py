"""
TutorialCompletionExit — special exit that completes a tutorial chunk.

When traversed, triggers instance collapse with graduation reward.
Placed at the end of each tutorial chunk, leading back to the hub.
"""

from evennia import ScriptDB
from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware


class TutorialCompletionExit(ExitVerticalAware):
    """Exit that triggers tutorial completion when traversed."""

    tutorial_instance_id = AttributeProperty(None)

    def at_post_traverse(self, traversing_object, source_location, **kwargs):
        """After the character has moved through, collapse the instance."""
        super().at_post_traverse(traversing_object, source_location, **kwargs)

        if not self.tutorial_instance_id:
            return

        # Find the instance script
        try:
            script = ScriptDB.objects.get(id=self.tutorial_instance_id)
        except ScriptDB.DoesNotExist:
            return

        if hasattr(script, "collapse_instance"):
            script.collapse_instance(give_reward=True)

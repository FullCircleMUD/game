"""
QuestDungeonTriggerExit — dungeon trigger with quest-based gating.

Extends DungeonTriggerExit to check quest completion before deciding
whether to create a dungeon instance or allow normal passage.

If the quest is active (accepted, not completed): creates a dungeon instance.
Otherwise (not accepted, or already completed): normal exit to fallback_destination.

Players must accept the quest from the quest-giving NPC before the
dungeon will spawn.
"""

from evennia import AttributeProperty

from typeclasses.terrain.exits.dungeon_trigger_exit import DungeonTriggerExit


class QuestDungeonTriggerExit(DungeonTriggerExit):
    """
    A dungeon trigger exit that gates entry on quest state.

    Builder usage:
        trigger = create_object(
            QuestDungeonTriggerExit,
            key="a small wooden door",
            location=cellar_stairwell,
            destination=cellar_stairwell,  # self-referential
        )
        trigger.dungeon_template_id = "rat_cellar"
        trigger.quest_key = "rat_cellar"
        trigger.fallback_destination_id = permanent_cellar.id
    """

    quest_key = AttributeProperty(None)
    fallback_destination_id = AttributeProperty(None)

    def _move_to_fallback(self, traversing_object):
        """Send the traverser to the fallback (non-dungeon) destination."""
        from evennia import ObjectDB

        try:
            dest = ObjectDB.objects.get(id=self.fallback_destination_id)
            traversing_object.move_to(dest)
        except ObjectDB.DoesNotExist:
            traversing_object.msg("The passage seems blocked.")

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """
        Route based on quest state:
          - Quest active (accepted, not completed) → dungeon instance
          - Quest not accepted or already completed → fallback destination
          - No quest_key configured → dungeon instance (backwards compat)
        """
        quest_key = self.quest_key

        if quest_key and hasattr(traversing_object, "quests"):
            quest_active = (
                traversing_object.quests.has(quest_key)
                and not traversing_object.quests.is_completed(quest_key)
            )

            if quest_active:
                # Quest in progress — create dungeon instance
                super().at_traverse(
                    traversing_object, target_location, **kwargs
                )
            else:
                # Not accepted or already completed — ordinary room
                self._move_to_fallback(traversing_object)
            return

        # No quest_key set — default dungeon trigger behaviour
        super().at_traverse(traversing_object, target_location, **kwargs)

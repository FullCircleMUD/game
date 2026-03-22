"""
VisitQuest — template for "visit location X" quests.

Progress fires when the character enters a room with matching quest_tags
via QuestTagMixin.fire_quest_event(character, "enter_room").

Example:
    @register_quest
    class ExploreTheRuins(VisitQuest):
        key = "explore_ruins"
        name = "Explore the Ancient Ruins"
        reward_xp = 50
"""

from world.quests.base_quest import FCMQuest


class VisitQuest(FCMQuest):
    """Template: visit a specific location."""

    start_step = "visit"

    help_visit = "Travel to the required location."

    def step_visit(self, *args, **kwargs):
        """Triggered by QuestTagMixin.fire_quest_event on room entry."""
        event_type = kwargs.get("event_type")
        if event_type == "enter_room":
            self.quester.msg("|gYou have reached your destination!|n")
            self.complete()

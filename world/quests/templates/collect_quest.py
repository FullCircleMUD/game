"""
CollectQuest — template for "bring me N of resource X" quests.

Subclass and set ``required_resources`` to define what's needed.
Progress is checked whenever ``check_progress`` is called on the
character's quest handler (typically from a guildmaster's CmdQuest
or similar NPC interaction).

Example:
    @register_quest
    class WarriorInitiation(CollectQuest):
        key = "warrior_initiation"
        name = "Trial of Arms"
        required_resources = {5: 3}  # 3 Iron Ingots
        consume_on_complete = True
        reward_xp = 100
"""

from world.quests.base_quest import FCMQuest


class CollectQuest(FCMQuest):
    """Template: collect resources and return to quest giver."""

    required_resources = {}  # {resource_id: amount} — override in subclass
    consume_on_complete = True  # take the resources as tribute?
    start_step = "collect"

    help_collect = "Gather the required resources and return."

    def step_collect(self, *args, **kwargs):
        """Check if character has all required resources."""
        for resource_id, amount in self.required_resources.items():
            if not self.quester.has_resource(resource_id, amount):
                return  # not done yet
        self.complete()

    def on_complete(self):
        if self.consume_on_complete:
            for resource_id, amount in self.required_resources.items():
                self.quester.return_resource_to_sink(resource_id, amount)

"""
MultiStepQuest — template for quests with an ordered sequence of objectives.

Each step is a dict describing what needs to happen. Steps auto-advance
when their condition is met.

Example:
    @register_quest
    class WarriorTrials(MultiStepQuest):
        key = "warrior_trials"
        name = "The Warrior's Trials"
        steps = [
            {"key": "gather", "type": "collect", "resources": {5: 3},
             "help": "Gather 3 Iron Ingots."},
            {"key": "deliver", "type": "visit",
             "help": "Return to the quest giver."},
        ]
"""

from world.quests.base_quest import FCMQuest


class MultiStepQuest(FCMQuest):
    """Template: ordered sequence of objectives.

    Subclass and override ``steps`` with a list of step dicts.
    Each step dict must have:
        key:  Step identifier string.
        type: Check method to use ("collect", "visit", "kill").
        help: Help text shown for this step.

    Optional per type:
        collect: resources = {resource_id: amount}
        kill:    target_type = str, count = int
    """

    steps = []  # override in subclass
    start_step = "0"  # index-based

    def progress(self, *args, **kwargs):
        """Check current step and advance if conditions met."""
        if self.is_completed or self.is_abandoned or self.is_failed:
            return
        step_idx = int(self.current_step)
        if step_idx >= len(self.steps):
            self.complete()
            return
        step_def = self.steps[step_idx]
        checker = getattr(self, f"_check_{step_def['type']}", None)
        if checker and checker(step_def, **kwargs):
            next_idx = step_idx + 1
            if next_idx >= len(self.steps):
                self.complete()
            else:
                self.current_step = str(next_idx)
                self.quester.msg(
                    f"|gObjective complete!|n {self.steps[next_idx].get('help', '')}"
                )

    def _check_collect(self, step_def, **kwargs):
        """Check if character has all required resources for this step."""
        for rid, amount in step_def.get("resources", {}).items():
            if not self.quester.has_resource(rid, amount):
                return False
        return True

    def _check_visit(self, step_def, **kwargs):
        """Check if this is a room entry event."""
        return kwargs.get("event_type") == "enter_room"

    def _check_kill(self, step_def, **kwargs):
        """Check kill count against target. Tracks kills in quest data."""
        if kwargs.get("event_type") != "kill":
            return False
        target_type = step_def.get("target_type")
        count_key = f"kills_{target_type}"
        current = self.get_data(count_key, 0) + 1
        self.add_data(count_key, current)
        return current >= step_def.get("count", 1)

    def help(self, *args, **kwargs):
        """Get help text for current step."""
        if self.is_completed:
            return self.help_completed
        if self.is_abandoned:
            return self.help_abandoned
        if self.is_failed:
            return self.help_failed
        step_idx = int(self.current_step) if self.current_step.isdigit() else 0
        if step_idx < len(self.steps):
            return self.steps[step_idx].get("help", "Continue your quest.")
        return "Quest complete!"

"""
Rats in the Cellar — the game's first combat quest.

Auto-accepted when the player enters the cellar dungeon instance.
Completes when the Rat King is killed (boss_killed event).
Once per playthrough (repeatable=False, resets on remort).
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest


@register_quest
class RatCellarQuest(FCMQuest):
    """Clear the rat infestation from the Harvest Moon cellar."""

    key = "rat_cellar"
    name = "Rats in the Cellar"
    desc = (
        "Rowan, the innkeeper of the Harvest Moon, has been hearing "
        "strange noises from the cellar. He's sure it's just rats, "
        "but someone needs to clear them out before they get into "
        "the ale supply."
    )
    quest_type = "main"
    start_step = "clear_cellar"
    reward_xp = 100
    reward_gold = 10
    repeatable = False

    help_clear_cellar = (
        "Enter the cellar beneath the Harvest Moon Inn and defeat "
        "the rats that have infested it. The cellar door is south "
        "of the Cellar Stairwell."
    )

    def step_clear_cellar(self, *args, **kwargs):
        """Progresses on boss_killed event fired by RatKing.die()."""
        event_type = kwargs.get("event_type")
        if event_type == "boss_killed":
            self.complete()

    def on_complete(self):
        """Notify the player."""
        self.quester.msg(
            "\n|yQuest Complete: Rats in the Cellar|n\n"
            "The cellar is safe once more. Rowan will be relieved "
            "to hear the news."
        )

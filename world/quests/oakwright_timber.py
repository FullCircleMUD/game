"""
Oakwright's Timber — starter delivery quest for Master Oakwright.

Oakwright's timber supplier hasn't delivered and his stock is running low.
The player helps by bringing 4 Timber (resource ID 7) to the workshop.

All 4 timber are consumed at once on delivery. Quest is non-repeatable and
only offered to characters with total level <= 3.

Turn-in happens via the ``quest`` command at the workshop — the
QuestGiverMixin's view handler calls ``progress()``, which triggers
``step_deliver_timber()`` to check inventory and complete.
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest

TIMBER_ID = 7
TIMBER_NEEDED = 4


@register_quest
class OakwrightTimberQuest(FCMQuest):
    """Deliver 4 timber to Master Oakwright."""

    key = "oakwright_timber"
    name = "Timber for the Workshop"
    desc = (
        "Master Oakwright's timber supplier hasn't delivered and his "
        "workshop stock is running low. He needs 4 Timber to keep "
        "working. The sawmill cuts wood into timber."
    )
    quest_type = "side"
    start_step = "deliver_timber"
    reward_xp = 100
    reward_gold = 5
    repeatable = False

    help_deliver_timber = (
        "Bring 4 Timber to Master Oakwright at his Woodshop. "
        "Timber can be cut from wood at the sawmill."
    )
    help_completed = (
        "You kept Oakwright's workshop running. He respects that."
    )

    def step_deliver_timber(self, *args, **kwargs):
        """Check for 4 timber, consume them, and complete."""
        if not self.quester.has_resource(TIMBER_ID, TIMBER_NEEDED):
            delivered = self.quester.get_resource(TIMBER_ID)
            remaining = TIMBER_NEEDED - delivered
            self.quester.msg(
                f"|rYou need {TIMBER_NEEDED} Timber. You have {delivered}. "
                f"Bring {remaining} more.|n"
            )
            return

        self.quester.return_resource_to_sink(TIMBER_ID, TIMBER_NEEDED)
        self.quester.msg(
            "|g*Oakwright inspects each piece carefully, then stacks them "
            "neatly by his workbench.* \"This'll do.\"|n"
        )
        self.complete()

    def on_complete(self):
        """Notify the player."""
        self.quester.msg(
            "\n|yQuest Complete: Timber for the Workshop|n\n"
            "Oakwright's workshop is stocked. He won't forget the help."
        )

"""
Mara's Moonpetal — starter delivery quest for Mara Brightwater.

A child in town has marsh fever and Mara needs fresh moonpetal for the
remedy. Her own supply wilted overnight and she can't leave the shop —
the poultice on the stove needs constant tending. The player helps by
bringing 3 Moonpetal (resource ID 12) to Mara at The Mortar and Pestle.

All 3 moonpetal are consumed at once on delivery. Quest is non-repeatable
and only offered to characters with total level <= 3.

Turn-in happens via the ``quest`` command at the apothecary — the
QuestGiverMixin's view handler calls ``progress()``, which triggers
``step_deliver_moonpetal()`` to check inventory and complete.
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest

MOONPETAL_ID = 12
MOONPETAL_NEEDED = 3


@register_quest
class MaraMoonpetalQuest(FCMQuest):
    """Deliver 3 moonpetal to Mara Brightwater."""

    key = "mara_moonpetal"
    name = "Moonpetal for the Remedy"
    desc = (
        "A child in Millholm has come down with marsh fever. Mara "
        "Brightwater needs 3 fresh Moonpetal to brew the remedy, but "
        "her supply wilted and she can't leave the shop — the poultice "
        "needs constant tending. Moonpetal grows in the fields south "
        "of town."
    )
    quest_type = "side"
    start_step = "deliver_moonpetal"
    reward_xp = 150
    reward_gold = 5
    reward_bread = 1
    repeatable = False
    account_cap = 10

    help_deliver_moonpetal = (
        "Bring 3 Moonpetal to Mara Brightwater at The Mortar and Pestle. "
        "Moonpetal grows in the fields south of town — look for the "
        "pale, luminous flowers."
    )
    help_completed = (
        "The child is recovering. Mara won't forget what you did."
    )

    def step_deliver_moonpetal(self, *args, **kwargs):
        """Check for 3 moonpetal, consume them, and complete."""
        if not self.quester.has_resource(MOONPETAL_ID, MOONPETAL_NEEDED):
            delivered = self.quester.get_resource(MOONPETAL_ID)
            remaining = MOONPETAL_NEEDED - delivered
            self.quester.msg(
                f"|rYou need {MOONPETAL_NEEDED} Moonpetal. You have "
                f"{delivered}. Bring {remaining} more.|n"
            )
            return

        self.quester.return_resource_to_sink(MOONPETAL_ID, MOONPETAL_NEEDED)
        self.quester.msg(
            "|g*Mara examines each moonpetal in turn, holding the pale "
            "petals to the light. She gives a small, satisfied nod and "
            "sets them beside the simmering poultice.* \"Fresh. Good.\"|n"
        )
        self.complete()

    def on_complete(self):
        """Notify the player."""
        self.quester.msg(
            "\n|yQuest Complete: Moonpetal for the Remedy|n\n"
            "The remedy is brewed. A child in Millholm will sleep "
            "soundly tonight."
        )

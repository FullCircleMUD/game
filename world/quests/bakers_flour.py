"""
Baker's Flour — starter delivery quest for Bron the Baker.

Bron's flour delivery from Goldwheat Farm hasn't arrived and he's running
low. The player helps by bringing 3 Flour (resource ID 2) to Bron.

All 3 flour are consumed at once on delivery. Quest is non-repeatable and
only offered to characters with total level <= 3.

Turn-in happens via the ``quest`` command at Bron's shop — the
QuestGiverMixin's view handler calls ``progress()``, which triggers
``step_deliver_flour()`` to check inventory and complete.
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest

FLOUR_ID = 2
FLOUR_NEEDED = 3


@register_quest
class BakersFlourQuest(FCMQuest):
    """Deliver 3 flour to Bron the baker."""

    key = "bakers_flour"
    name = "Flour for the Baker"
    desc = (
        "Bron the baker is in a bind — his regular flour delivery from "
        "Goldwheat Farm hasn't arrived and he's almost out. He needs "
        "3 Flour to keep the bakery running until the supply line is "
        "restored. The windmill at Goldwheat Farm grinds wheat into flour."
    )
    quest_type = "side"
    start_step = "deliver_flour"
    reward_xp = 100
    reward_gold = 4
    repeatable = False

    help_deliver_flour = (
        "Bring 3 Flour to Bron at the Goldencrust Bakery. "
        "Flour can be milled from wheat at the Goldwheat Farm windmill."
    )
    help_completed = (
        "You helped Bron keep the bakery running. He won't forget it."
    )

    def step_deliver_flour(self, *args, **kwargs):
        """Check for 3 flour, consume them, and complete."""
        if not self.quester.has_resource(FLOUR_ID, FLOUR_NEEDED):
            delivered = self.quester.get_resource(FLOUR_ID)
            remaining = FLOUR_NEEDED - delivered
            self.quester.msg(
                f"|rYou need {FLOUR_NEEDED} Flour. You have {delivered}. "
                f"Bring {remaining} more.|n"
            )
            return

        self.quester.return_resource_to_sink(FLOUR_ID, FLOUR_NEEDED)
        self.quester.msg(
            "|gBron beams as he takes the flour. "
            "\"This is exactly what I needed!\"|n"
        )
        self.complete()

    def on_complete(self):
        """Notify the player."""
        self.quester.msg(
            "\n|yQuest Complete: Flour for the Baker|n\n"
            "Bron's bakery is saved — for now. He's endlessly grateful."
        )

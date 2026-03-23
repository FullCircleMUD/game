"""
Hendricks' Bronze — starter delivery quest for Old Hendricks.

Hendricks needs bronze ingots to keep the forge productive. The player
must mine copper and tin ore from the abandoned mine, smelt them into
bronze at a smelter, and deliver 3 Bronze Ingot (resource ID 32).

This is the hardest of the starter quests — the mine is dangerous,
requires traversing the deep woods to reach, and the player must also
process the ore into ingots. Higher XP reward reflects the difficulty.

All 3 ingots are consumed at once on delivery. Quest is non-repeatable
and only offered to characters with total level <= 3.

Turn-in happens via the ``quest`` command at the smithy — the
QuestGiverMixin's view handler calls ``progress()``, which triggers
``step_deliver_ingots()`` to check inventory and complete.
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest

BRONZE_INGOT_ID = 32
INGOTS_NEEDED = 3


@register_quest
class HendricksOreQuest(FCMQuest):
    """Deliver 3 bronze ingots to Old Hendricks."""

    key = "hendricks_ore"
    name = "Bronze for the Forge"
    desc = (
        "Old Hendricks is running low on bronze. He needs 3 Bronze "
        "Ingots to keep the forge running. Bronze is smelted from "
        "copper and tin ore — both can be mined in the abandoned mine "
        "north-east of town, through the deep woods. The mine is "
        "dangerous and the smelting adds work, but Hendricks pays well."
    )
    quest_type = "side"
    start_step = "deliver_ingots"
    reward_xp = 250
    reward_gold = 10
    repeatable = False
    account_cap = 10

    help_deliver_ingots = (
        "Bring 3 Bronze Ingots to Old Hendricks at his smithy. "
        "Mine copper and tin ore from the abandoned mine north-east "
        "of town, then smelt them into bronze ingots at a smelter."
    )
    help_completed = (
        "You braved the mine and kept Hendricks' forge stocked with "
        "bronze. He won't say much about it, but he respects you for it."
    )

    def step_deliver_ingots(self, *args, **kwargs):
        """Check for 3 bronze ingots, consume them, and complete."""
        if not self.quester.has_resource(BRONZE_INGOT_ID, INGOTS_NEEDED):
            delivered = self.quester.get_resource(BRONZE_INGOT_ID)
            remaining = INGOTS_NEEDED - delivered
            self.quester.msg(
                f"|rYou need {INGOTS_NEEDED} Bronze Ingots. You have "
                f"{delivered}. Bring {remaining} more.|n"
            )
            return

        self.quester.return_resource_to_sink(BRONZE_INGOT_ID, INGOTS_NEEDED)
        self.quester.msg(
            "|g*Hendricks weighs an ingot in his palm, then raps it "
            "against the anvil, listening to the ring. He gives a "
            "single nod.* \"Good alloy. That'll do.\"|n"
        )
        self.complete()

    def on_complete(self):
        """Notify the player."""
        self.quester.msg(
            "\n|yQuest Complete: Bronze for the Forge|n\n"
            "Hendricks' forge has bronze again. From him, silence "
            "is approval."
        )

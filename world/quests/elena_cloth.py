"""
Elena's Cloth — starter delivery quest for Elena Copperkettle.

Elena is in a panic — the mayor's daughter's wedding is this weekend and
she's run out of cloth for the dress. The player helps by bringing 3 Cloth
(resource ID 11) to Elena at her cottage.

All 3 cloth are consumed at once on delivery. Quest is non-repeatable and
only offered to characters with total level <= 3.

Turn-in happens via the ``quest`` command at Elena's cottage — the
QuestGiverMixin's view handler calls ``progress()``, which triggers
``step_deliver_cloth()`` to check inventory and complete.
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest

CLOTH_ID = 11
CLOTH_NEEDED = 3


@register_quest
class ElenaClothQuest(FCMQuest):
    """Deliver 3 cloth to Elena Copperkettle."""

    key = "elena_cloth"
    name = "Cloth for the Wedding Dress"
    desc = (
        "Elena Copperkettle is in a panic — the mayor's daughter's "
        "wedding is this weekend and she's three bolts of cloth short "
        "for the dress. She needs 3 Cloth urgently. Cotton can be "
        "woven into cloth at the loom in Millhaven Textiles."
    )
    quest_type = "side"
    start_step = "deliver_cloth"
    reward_xp = 100
    reward_gold = 5
    repeatable = False

    help_deliver_cloth = (
        "Bring 3 Cloth to Elena Copperkettle at her cottage. "
        "Cloth can be woven from cotton at the loom in Millhaven Textiles."
    )
    help_completed = (
        "You saved Elena from disaster. The wedding dress will be "
        "finished on time — thanks to you."
    )

    def step_deliver_cloth(self, *args, **kwargs):
        """Check for 3 cloth, consume them, and complete."""
        if not self.quester.has_resource(CLOTH_ID, CLOTH_NEEDED):
            delivered = self.quester.get_resource(CLOTH_ID)
            remaining = CLOTH_NEEDED - delivered
            self.quester.msg(
                f"|rYou need {CLOTH_NEEDED} Cloth. You have {delivered}. "
                f"Bring {remaining} more.|n"
            )
            return

        self.quester.return_resource_to_sink(CLOTH_ID, CLOTH_NEEDED)
        self.quester.msg(
            "|g*Elena snatches the cloth and immediately starts unrolling "
            "a bolt, holding it up to the light.* \"Oh, the weave on "
            "this — yes, yes, this will do perfectly!\"|n"
        )
        self.complete()

    def on_complete(self):
        """Notify the player."""
        self.quester.msg(
            "\n|yQuest Complete: Cloth for the Wedding Dress|n\n"
            "The mayor's daughter will have her dress. Elena won't "
            "stop thanking you for a week."
        )

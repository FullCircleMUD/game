"""
Test Initiation — a trivial guild quest for the test world.

Test scaffolding, not content. One shared quest that every test-world
guildmaster can point at, so a tester can unlock guild membership without
running a real initiation.

Objective: hold at least 1 wheat (resource ID 1), then type ``quest``.

Unlike the real initiation quests, this one does NOT grant a class on
completion — it cannot, because it is shared by guildmasters of different
classes. Completing it satisfies the guildmaster's quest gate; the tester
then types ``join`` at whichever guildmaster they want.

The wheat is not consumed, so the same wheat unlocks every guildmaster.
"""

from world.quests import register_quest
from world.quests.base_quest import FCMQuest

WHEAT_RESOURCE_ID = 1


@register_quest
class TestInitiation(FCMQuest):
    key = "test_initiation"
    name = "Test Initiation"
    desc = (
        "\"Before I take you seriously, bring me a bushel of wheat. "
        "One is enough. Then come back and say so.\""
    )
    quest_type = "guild"
    start_step = "get_wheat"
    reward_xp = 0

    help_get_wheat = (
        "Obtain at least 1 wheat, then return to a guildmaster and type "
        "|wquest|n."
    )
    help_completed = (
        "You brought the wheat. Type |wjoin|n at a guildmaster to join "
        "their guild."
    )

    # ── Step method ──

    def step_get_wheat(self, *args, **kwargs):
        """Complete once the character holds at least 1 wheat."""
        held = self.quester.get_resource(WHEAT_RESOURCE_ID)
        if held >= 1:
            self.quester.msg(
                "\n|yThe guildmaster inspects your wheat and grunts. "
                "\"Good enough.\"|n\n"
            )
            self.complete()
        else:
            self.quester.msg(
                "|rThe guildmaster shakes their head. \"No wheat, no "
                "membership. Come back with a bushel.\"|n"
            )

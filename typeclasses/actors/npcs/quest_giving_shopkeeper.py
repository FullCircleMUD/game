"""
QuestGivingShopkeeper — LLM shopkeeper NPC that also gives quests.

Extends LLMShopkeeperNPC with QuestGiverMixin for quest accept/abandon/
view/turn-in. The LLM prompt receives both {quest_context} and
{shop_commands} template variables.

Subclass this for specific NPCs (e.g. BakerNPC) — override
``_build_quest_context()`` to inject quest-specific state detection,
and ``get_quest_completion_message()`` for custom completion text.

Usage (spawn script)::

    npc = create_object(
        "typeclasses.actors.npcs.quest_giving_shopkeeper.QuestGivingShopkeeper",
        key="Bron",
        location=room,
    )
    npc.tradeable_resources = [2, 3]   # flour, bread
    npc.shop_name = "Goldencrust Bakery"
    npc.quest_key = "bakers_flour"
    npc.llm_prompt_file = "baker.md"
    npc.llm_personality = "A flour-dusted baker..."
"""

from typeclasses.actors.npcs.llm_shopkeeper_npc import LLMShopkeeperNPC
from typeclasses.mixins.quest_giver import QuestGiverMixin


class QuestGivingShopkeeper(QuestGiverMixin, LLMShopkeeperNPC):
    """
    LLM shopkeeper NPC with quest commands and quest-aware context.

    Adds to LLMShopkeeperNPC:
    - QuestGiverMixin for quest accept/abandon/view/turn-in via ``quest`` command
    - Quest-aware context injection via {quest_context} template variable

    Configuration (set per instance):
        quest_key: quest key this NPC offers (from QuestGiverMixin)
        tradeable_resources: list of int resource IDs (from LLMShopkeeperNPC)
        shop_name: display name for the shop (from LLMShopkeeperNPC)
        llm_prompt_file: prompt template with {quest_context} and {shop_commands}
    """

    # Level gate — experienced players get generic prompts
    STARTER_LEVEL_CAP = 3

    # ── Context variable injection ────────────────────────────────────

    def _get_context_variables(self):
        context = super()._get_context_variables()

        # Inject quest context based on the current speaker's state
        speaker = getattr(self.ndb, "_llm_current_speaker", None)
        if speaker:
            context["quest_context"] = self._build_quest_context(speaker)
        else:
            context["quest_context"] = ""

        return context

    def _build_quest_context(self, character):
        """
        Build state-specific LLM instructions based on the player's state.

        Override this in subclasses to implement NPC-specific quest logic.
        The default returns an empty string (no quest agenda).
        """
        return ""

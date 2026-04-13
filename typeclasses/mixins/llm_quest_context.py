"""
LLMQuestContextMixin — inject {quest_context} into LLM prompts.

A tiny cooperative mixin for LLM NPCs that are also quest-aware. Owns just
the injection of a single template variable (`quest_context`) into the
prompt context dict, and declares the `_build_quest_context(character)`
hook that subclasses override to return a state-specific prompt block.

The mixin makes no assumptions about shopkeeping, training, or any other
role. Compose it alongside any LLM-capable NPC class and a quest source:

    class BakerNPC(
        LLMQuestContextMixin,
        QuestGiverMixin,
        LLMResourceShopkeeperNPC,
    ):
        def _build_quest_context(self, character):
            ...

    class LLMQuestGiverNPC(
        LLMQuestContextMixin,
        QuestGiverMixin,
        LLMRoleplayNPC,
    ):
        ...  # pure LLM quest giver, no shop or training

The injection is gated on ``self.ndb._llm_current_speaker`` being set —
this is populated by the LLM mixin immediately before prompt rendering
so the NPC knows which player's state to describe. If no speaker is set
the context value is an empty string (harmless for templates that
reference ``{quest_context}`` unconditionally).
"""


class LLMQuestContextMixin:
    """Injects ``{quest_context}`` into LLM prompt context."""

    def _get_context_variables(self):
        context = super()._get_context_variables()
        speaker = getattr(self.ndb, "_llm_current_speaker", None)
        context["quest_context"] = (
            self._build_quest_context(speaker) if speaker else ""
        )
        return context

    def _build_quest_context(self, character):
        """Override in concrete NPC to return the state-specific prompt block.

        Default returns empty string so mixing this in without overriding
        is a no-op rather than a bug.
        """
        return ""

"""
LLMGuildmasterNPC — LLM-powered guildmaster with quest-giving.

Combines LLMMixin (LLM dialogue with vector memory support) and
GuildmasterNPC (multiclassing + level advancement + guild commands).
The LLM prompt receives {quest_context} and {guild_commands} blocks
so the NPC can naturally guide players.

Follows the same pattern as QuestGivingLLMTrainer but for guildmasters.

Usage (spawn script)::

    npc = create_object(
        "typeclasses.actors.npcs.llm_guildmaster_npc.LLMGuildmasterNPC",
        key="Gareth Stonefield",
        location=room,
    )
    npc.guild_class = "thief"
    npc.multi_class_quest_key = "thief_initiation"
    npc.max_advance_level = 5
    npc.llm_personality = "An impeccably dressed merchant..."
    npc.llm_use_vector_memory = True
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npcs.guildmaster import GuildmasterNPC
from typeclasses.mixins.llm_mixin import LLMMixin


class LLMGuildmasterNPC(LLMMixin, GuildmasterNPC):
    """
    LLM-powered guildmaster NPC.

    Combines:
    - LLMMixin for LLM dialogue (personality, memory, speech detection)
    - GuildmasterNPC (QuestGiverMixin + BaseNPC) for guild/join/advance
      commands and quest accept/abandon/view/turn-in

    Configuration (set per instance):
        guild_class: character class key (e.g. "thief")
        multi_class_quest_key: quest gate for multiclass
        max_advance_level: level cap for this guildmaster
        next_guildmaster_hint: redirect flavour text
        llm_personality: character voice and traits
        llm_knowledge: factual lore and rules
        llm_use_vector_memory: True for persistent semantic memory
    """

    llm_prompt_file = AttributeProperty("roleplay_npc.md")
    llm_use_vector_memory = AttributeProperty(False)

    def at_object_creation(self):
        super().at_object_creation()
        self.at_llm_init()

    def llm_fallback_response(self, speaker, interaction_type):
        """Fallback when LLM is unavailable."""
        if interaction_type == "sayto":
            return f"*regards {speaker.key} with a measured gaze*"
        return None

    # ── Context variable injection ────────────────────────────────────

    def _get_context_variables(self):
        context = super()._get_context_variables()

        speaker = getattr(self.ndb, "_llm_current_speaker", None)
        if speaker:
            context["quest_context"] = self._build_quest_context(speaker)
        else:
            context["quest_context"] = ""

        context["guild_commands"] = self._build_guild_commands()
        return context

    def _build_quest_context(self, character):
        """
        Build state-specific LLM instructions based on the player's state.

        Override this in subclasses for NPC-specific quest logic.
        """
        return ""

    def _build_guild_commands(self):
        """Build a formatted block of guild commands for the LLM prompt."""
        lines = [
            "GUILD COMMANDS (tell players these when they ask about the guild):",
            "  |wguild|n — see guild info, requirements, and your progress",
            "  |wquest|n — view, accept, or turn in the initiation quest",
            "  |wjoin|n — become a member of the guild (if quest complete)",
            "  |wadvance|n — spend a level on this class",
        ]
        return "\n".join(lines)

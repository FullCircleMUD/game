"""
QuestGivingLLMTrainer — LLM-powered trainer NPC with quest-giving.

Combines QuestGiverMixin (quest accept/abandon/view/turn-in command),
LLMMixin (LLM dialogue with quest-aware context injection), and
TrainerNPC (skill training + recipe sales). The LLM prompt receives
a {quest_context} block (state-specific instructions) and a
{train_commands} block (available training commands) so the NPC can
naturally guide players.

Subclass this for specific NPCs (e.g. OakwrightNPC) — override
``_build_quest_context()`` for quest-specific state detection and
``get_quest_completion_message()`` for custom completion text.

Usage (spawn script)::

    npc = create_object(
        "typeclasses.actors.npcs.quest_giving_llm_trainer.QuestGivingLLMTrainer",
        key="Master Oakwright",
        location=room,
    )
    npc.trainable_skills = ["carpentry"]
    npc.trainer_masteries = {"carpentry": 2}
    npc.quest_key = "oakwright_timber"
    npc.llm_prompt_file = "oakwright.md"
    npc.llm_personality = "A taciturn master carpenter..."
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npcs.trainer import TrainerNPC
from typeclasses.mixins.llm_mixin import LLMMixin
from typeclasses.mixins.quest_giver import QuestGiverMixin


class QuestGivingLLMTrainer(QuestGiverMixin, LLMMixin, TrainerNPC):
    """
    LLM-powered trainer NPC with quest commands and quest-aware context.

    Combines:
    - QuestGiverMixin for quest accept/abandon/view/turn-in via ``quest`` command
    - LLMMixin for LLM dialogue (personality, memory, speech detection)
    - TrainerNPC for skill training and recipe sales via ``train`` command
    - Quest-aware context injection via {quest_context} template variable
    - Training command descriptions via {train_commands} template variable

    Configuration (set per instance):
        quest_key: quest key this NPC offers (from QuestGiverMixin)
        trainable_skills: list of skill key strings this trainer teaches
        trainer_masteries: dict mapping skill key to max mastery int (1-5)
        trainer_class: character class this trainer serves (None for general)
        llm_prompt_file: prompt template with {quest_context} and {train_commands}
        llm_use_vector_memory: defaults to False (short-term memory only)

    Subclasses should override ``_build_quest_context()`` for NPC-specific
    quest state detection and ``get_quest_completion_message()`` for
    custom completion text.
    """

    llm_prompt_file = AttributeProperty("roleplay_npc.md")
    llm_use_vector_memory = AttributeProperty(False)

    # Level gate — experienced players get generic prompts
    STARTER_LEVEL_CAP = 3

    def at_object_creation(self):
        super().at_object_creation()
        self.at_llm_init()

    def llm_fallback_response(self, speaker, interaction_type):
        """Fallback when LLM is unavailable."""
        if interaction_type == "sayto":
            return f"*nods at {speaker.key} briefly*"
        return None

    # ── Context variable injection ────────────────────────────────────

    def _get_context_variables(self):
        context = super()._get_context_variables()

        speaker = getattr(self.ndb, "_llm_current_speaker", None)
        if speaker:
            context["quest_context"] = self._build_quest_context(speaker)
        else:
            context["quest_context"] = ""

        context["train_commands"] = self._build_train_commands()
        return context

    def _build_quest_context(self, character):
        """
        Build state-specific LLM instructions based on the player's state.

        Override this in subclasses to implement NPC-specific quest logic.
        The default returns an empty string (no quest agenda).
        """
        return ""

    def _build_train_commands(self):
        """
        Build a formatted block of training commands for the LLM prompt.

        Includes command syntax and a list of skills this trainer teaches.
        """
        lines = [
            "TRAINING COMMANDS (tell players these when they ask about training):",
            "  |wtrain|n — see available skills and costs",
            "  |wtrain <skill>|n — train a skill (costs gold + skill points)",
        ]

        recipes = dict(self.recipes_for_sale or {})
        if recipes:
            lines.append("  |wbuy recipe|n — see recipes for sale")
            lines.append("  |wbuy recipe <name>|n — purchase a recipe")

        skills = list(self.trainable_skills or [])
        if skills:
            skill_names = [s.replace("_", " ").title() for s in skills]
            lines.append(f"\nYou teach: {', '.join(skill_names)}.")

        return "\n".join(lines)

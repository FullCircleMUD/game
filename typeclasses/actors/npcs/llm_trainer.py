"""
LLMTrainerNPC — LLM-powered trainer NPC.

Combines ``LLMRoleplayNPC`` (personality, memory, speech detection) with
``TrainerNPC`` (skill training + recipe sales via the ``train`` command).
Injects a ``{train_commands}`` block into the LLM prompt so the model
knows which training commands exist and which skills this NPC teaches.

This is the non-quest-aware base for LLM trainers. NPCs that also give
quests compose ``LLMQuestContextMixin`` + ``QuestGiverMixin`` on top:

    class OakwrightNPC(
        LLMQuestContextMixin,
        QuestGiverMixin,
        LLMTrainerNPC,
    ):
        quest_key = "oakwright_timber"
        ...

NPCs that don't give quests (e.g. Gemma the jeweller, Old Barnacle Bob)
instantiate ``LLMTrainerNPC`` directly via their spawn script.

Configuration (set per instance):
    trainable_skills: list of skill key strings this trainer teaches
    trainer_masteries: dict {skill_key: mastery_int}
    trainer_class: character class key (e.g. "warrior") or None
    recipes_for_sale: dict {recipe_key: gold_cost}
    llm_personality: character voice and traits
    llm_use_vector_memory: defaults to False (short-term memory only)
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC
from typeclasses.actors.npcs.trainer import TrainerNPC


class LLMTrainerNPC(LLMRoleplayNPC, TrainerNPC):
    """LLM-powered trainer NPC. Use directly, or compose with quest mixins."""

    llm_prompt_file = AttributeProperty("roleplay_npc.md")
    llm_use_vector_memory = AttributeProperty(False)

    # Level gate — experienced players get generic prompts. Subclasses
    # that care about this cap read it from ``_build_quest_context``.
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
        context["train_commands"] = self._build_train_commands()
        return context

    def _build_train_commands(self):
        """Formatted block of training commands for the LLM prompt.

        Lists the train/buy-recipe commands and the skills this trainer
        teaches, so the LLM can naturally guide players to the right
        commands rather than fake the interaction in dialogue.
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

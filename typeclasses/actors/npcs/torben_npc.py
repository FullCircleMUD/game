"""
TorbenNPC — Torben Greaves, leatherworking trainer at The Tanned Hide.

Composed of LLMQuestContextMixin + QuestGiverMixin + LLMTrainerNPC. No
quest assigned — ``_build_quest_context()`` always returns generic
context so the LLM prompt still receives the personality instructions
block via the quest-context injection path.

Trains leatherworking to SKILLED level (mastery 2).
Short-term memory only (no vector embeddings).
"""

from typeclasses.actors.npcs.llm_trainer import LLMTrainerNPC
from typeclasses.mixins.llm_quest_context import LLMQuestContextMixin
from typeclasses.mixins.quest_giver import QuestGiverMixin


# ── Shared knowledge block ────────────────────────────────────────────

_TORBEN_KNOWLEDGE = (
    "You are Torben Greaves, the leatherworker at The Tanned Hide in "
    "Millholm. You've been working hides since you were old enough to "
    "hold a knife. Your father was a tanner, and his father before him. "
    "You're patient and methodical — good leather can't be rushed. You "
    "take pride in your work and get quietly irritated when people don't "
    "appreciate the difference between proper cured leather and the "
    "cheap stuff. You train apprentices in leatherworking. You smell "
    "faintly of tanning chemicals, and you've stopped noticing."
)

_COMMON_RULES = (
    "RULES:\n"
    "- Stay in character. You ARE {name}, the leatherworker.\n"
    "- Keep responses to 1-2 sentences. You're patient but not chatty.\n"
    "- You may use *emotes* sparingly (e.g. *runs a thumb along a "
    "leather strap, testing the grain*).\n"
    "- When suggesting commands, format them as |w<command>|n.\n"
    "- NEVER break character or mention being an AI.\n"
    "- If asked something you wouldn't logically know, say so in character.\n"
    "- Your speech is steady, unhurried, practical. You explain things "
    "in terms of craft — grain, cure, cut. No wasted words, but "
    "you'll talk at length about leather if someone shows interest."
)

# ── Context block (trainer only — no quest states) ─────────────────────

GENERIC_CONTEXT = (
    f"What you know:\n{_TORBEN_KNOWLEDGE}\n\n"
    "CURRENT SITUATION: This is a visitor to your shop.\n"
    "YOUR GOAL: Be a steady, practical craftsman. If they want to "
    "learn leatherworking, you can teach them — tell them to type "
    "|wtrain|n to see what you offer. You might show them something "
    "you're working on if they seem interested. You're not unfriendly, "
    "just unhurried. Good leather takes time, and so do good "
    "conversations.\n\n"
    f"{_COMMON_RULES}"
)


class TorbenNPC(LLMQuestContextMixin, QuestGiverMixin, LLMTrainerNPC):
    """Trainer NPC for Torben Greaves at The Tanned Hide."""

    def _build_quest_context(self, character):
        """Torben has no quest — always returns generic context."""
        return GENERIC_CONTEXT

    def get_quest_completion_message(self, caller, quest):
        """Not used — Torben has no quest."""
        return ""

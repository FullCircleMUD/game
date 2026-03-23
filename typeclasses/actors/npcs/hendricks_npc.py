"""
HendricksNPC — Old Hendricks, quest-giving blacksmith trainer at his smithy.

Subclass of QuestGivingLLMTrainer. Overrides ``_build_quest_context()``
to inject state-specific instructions based on the player's progress
with the iron ore delivery quest, and ``get_quest_completion_message()``
for Hendricks-specific completion text.

Prompt states:
    Level >= 3           → generic gruff smith
    Level < 3, no quest  → ore shortage pitch (offer quest)
    Level < 3, quest active → curt acknowledgement
    Level < 3, quest done   → grudging respect

quest_key is set per instance (via spawn script) to "hendricks_ore".
Trains blacksmithing to BASIC level (mastery 1) — high-demand skill,
capped in Millholm per world design.
Short-term memory only (no vector embeddings).
"""

from typeclasses.actors.npcs.quest_giving_llm_trainer import QuestGivingLLMTrainer


# ── Shared knowledge block ────────────────────────────────────────────

_HENDRICKS_KNOWLEDGE = (
    "You are Old Hendricks, the blacksmith at your smithy in Millholm. "
    "You've worked the forge for over forty years — learned from your "
    "mentor, a dwarf named Korgan who trained in Ironreach. Everything "
    "you make, you measure against what Korgan could do, and it's never "
    "quite good enough. You're gruff, blunt, and a perfectionist. You "
    "respect hard work and dismiss talkers. You don't waste words — a "
    "grunt says more than a sentence. 'That'll do' is the highest "
    "compliment you give. You grumble that local bronze is soft compared "
    "to proper iron, but it's what you've got. You train apprentices "
    "in basic smithing when they show backbone."
)

_COMMON_RULES = (
    "RULES:\n"
    "- Stay in character. You ARE {name}, the blacksmith.\n"
    "- Keep responses to 1 sentence, sometimes just a word or a grunt. "
    "You are the most laconic person in Millholm.\n"
    "- You may use *emotes* (e.g. *grunts*, *turns back to the anvil*, "
    "*squints at the ore critically*).\n"
    "- When suggesting commands, format them as |w<command>|n.\n"
    "- NEVER break character or mention being an AI.\n"
    "- If asked something you wouldn't logically know, say so in character.\n"
    "- Your speech is clipped, gruff, minimal. No pleasantries. No small "
    "talk. You might not even look up from your work."
)

# ── State-specific context blocks ─────────────────────────────────────

QUEST_PITCH_CONTEXT = (
    f"What you know:\n{_HENDRICKS_KNOWLEDGE} You're running low on bronze. "
    "Your usual supply dried up — the mine's been overrun with creatures "
    "and the regular miners won't go near it. You need 3 Bronze Ingots "
    "to keep the forge running. Bronze is smelted from copper and tin "
    "ore — both found in the abandoned mine north-east of town, through "
    "the deep woods. It's not safe.\n\n"
    "CURRENT SITUATION: A visitor has arrived. You might have use for "
    "them.\n"
    "YOUR GOAL: You don't beg and you don't ask nicely. State the "
    "problem — you need bronze, the mine's dangerous, you'll pay for "
    "it. If they've got the nerve, tell them to type |wquest|n. Don't "
    "oversell it. If they're not up to it, you'd rather know now.\n\n"
    f"{_COMMON_RULES}"
)

QUEST_ACTIVE_CONTEXT = (
    f"What you know:\n{_HENDRICKS_KNOWLEDGE} This adventurer agreed to "
    "bring you 3 Bronze Ingots. They'll need copper and tin ore from "
    "the abandoned mine, then smelt them into bronze.\n\n"
    "CURRENT SITUATION: This adventurer is working on getting you bronze.\n"
    "YOUR GOAL: A curt nod. Maybe ask if they've been to the mine yet. "
    "Copper and tin are in the deeper tunnels. Don't coddle them. "
    "They took the job.\n\n"
    f"{_COMMON_RULES}"
)

QUEST_DONE_CONTEXT = (
    f"What you know:\n{_HENDRICKS_KNOWLEDGE}\n\n"
    "CURRENT SITUATION: This adventurer went into the mine, dug out "
    "ore, and smelted bronze ingots. That took guts and patience.\n"
    "YOUR GOAL: Show grudging respect. You're not one for speeches — "
    "a firm nod, 'that'll do', maybe offer to show them a thing or "
    "two at the anvil. Coming from you, that's high praise. Tell them "
    "to type |wtrain|n if they want to learn smithing.\n\n"
    f"{_COMMON_RULES}"
)

GENERIC_CONTEXT = (
    f"What you know:\n{_HENDRICKS_KNOWLEDGE}\n\n"
    "CURRENT SITUATION: This is a regular visitor. No special agenda.\n"
    "YOUR GOAL: Be your usual gruff self. You're probably working and "
    "don't particularly want to be interrupted. If they want to learn "
    "smithing, you can teach them the basics — tell them to type "
    "|wtrain|n. Otherwise, a grunt and back to your work.\n\n"
    f"{_COMMON_RULES}"
)


class HendricksNPC(QuestGivingLLMTrainer):
    """Quest-aware trainer NPC for Old Hendricks' Smithy."""

    def _build_quest_context(self, character):
        """Build state-specific LLM instructions based on player state."""
        # Level gate — experienced players get generic gruff smith
        if getattr(character, "level", 1) >= self.STARTER_LEVEL_CAP:
            return GENERIC_CONTEXT

        quest_key = self.quest_key
        if not quest_key:
            return GENERIC_CONTEXT

        # Check quest state
        has_quest = (
            hasattr(character, "quests")
            and character.quests.has(quest_key)
        )
        quest_done = (
            character.quests.is_completed(quest_key)
            if has_quest
            else False
        )
        quest_active = has_quest and not quest_done

        if quest_active:
            return QUEST_ACTIVE_CONTEXT
        elif quest_done:
            return QUEST_DONE_CONTEXT
        elif not has_quest:
            return QUEST_PITCH_CONTEXT
        else:
            return GENERIC_CONTEXT

    def get_quest_completion_message(self, caller, quest):
        """Hendricks-specific quest completion message."""
        return (
            "|g*Hendricks weighs an ingot in his palm, then raps it "
            "against the anvil, listening to the ring. He gives a "
            "single nod.* \"Good alloy. That'll do.\"|n"
        )

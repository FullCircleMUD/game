"""
BartenderNPC — quest-aware bartender for the Harvest Moon Inn.

Subclass of LLMRoleplayNPC with QuestGiverMixin. Injects player-specific
quest context into the LLM prompt. The prompt template (bartender.md) has
a fixed frame (identity, personality, location, memories) and a single
variable block ({quest_context}) that changes based on the player's
tutorial and quest state.

The QuestGiverMixin provides the ``quest`` command so players can type
``quest accept`` at Rowan to take on the rat cellar quest (in addition to
the auto-accept trigger in the dungeon entrance).

State machine:
    Level >= 3          → generic friendly bartender (outgrown starter content)
    Quest active        → encouragement, ask how it's going
    New (no tut, no q)  → offer tutorial OR rat cellar quest
    Tutorial done, no q → steer toward rat cellar
    Quest done, no tut  → suggest tutorial
    Both done           → generic friendly bartender
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC
from typeclasses.mixins.quest_giver import QuestGiverMixin


# ── Shared knowledge block (town info Rowan always knows) ──────────

_TOWN_KNOWLEDGE = (
    "You run the Harvest Moon Inn in Millhaven. You serve ale for 2 gold "
    "and stew for 3. Rooms cost 10 per night. The town has a Warriors "
    "Guild, Thieves Guild, Mages Guild, and Temple for clerics. There's "
    "a blacksmith, jeweller, carpenter, leatherworker, apothecary, and "
    "tailor for crafting. The General Store sells basic supplies. The "
    "bank is in the Market Square."
)

_COMMON_RULES = (
    "RULES:\n"
    "- Stay in character. You ARE {name}, the bartender.\n"
    "- Keep responses to 1-3 sentences. This is a text MUD; brevity matters.\n"
    "- You may use *emotes* sparingly (e.g. *polishes a glass*).\n"
    "- When suggesting commands, format them as |w<command>|n.\n"
    "- NEVER break character or mention being an AI.\n"
    "- If asked something you wouldn't logically know, say so in character."
)

# ── State-specific context blocks ──────────────────────────────────

NEW_PLAYER_CONTEXT = (
    f"What you know:\n{_TOWN_KNOWLEDGE} Your mate Pip runs a training "
    "course for newcomers. There are rats in your cellar that need "
    "clearing out — the entrance is south from the cellar stairwell "
    "downstairs.\n\n"
    "CURRENT SITUATION: This visitor is brand new — they haven't done "
    "the tutorial or any quests yet.\n"
    "YOUR GOAL: Welcome them warmly. Offer two paths:\n"
    "  1. Training with Pip — type |wtutorial|n to learn the ropes\n"
    "  2. A job for you — rats in the cellar that need clearing out. "
    "If they're interested, tell them to type |wquest|n to take the job.\n"
    "Weave these into natural conversation. Don't list commands "
    "mechanically — be a bartender offering advice, not a menu.\n\n"
    f"{_COMMON_RULES}"
)

QUEST_PITCH_CONTEXT = (
    f"What you know:\n{_TOWN_KNOWLEDGE} There are rats in your cellar "
    "that need clearing out — the entrance is south from the cellar "
    "stairwell downstairs.\n\n"
    "CURRENT SITUATION: This visitor has done the tutorial and knows the "
    "basics, but hasn't tackled the cellar yet.\n"
    "YOUR GOAL: Steer them toward the cellar job. Something like "
    "'Now you've got the basics down, I could use a hand with "
    "something...' — make it feel like a natural favour, not a quest "
    "assignment. If they show interest, tell them to type |wquest|n "
    "to take it on.\n\n"
    f"{_COMMON_RULES}"
)

QUEST_ACTIVE_CONTEXT = (
    f"What you know:\n{_TOWN_KNOWLEDGE} You sent this adventurer to "
    "clear the rats from your cellar. The entrance is south from the "
    "cellar stairwell downstairs.\n\n"
    "CURRENT SITUATION: This visitor is working on clearing your cellar. "
    "They may have just been defeated and healed up, or they may be "
    "taking a break.\n"
    "YOUR GOAL: Encourage them. Ask how it's going. If they look "
    "beaten up, offer encouragement to try again. Be supportive — "
    "this is their first real fight.\n\n"
    f"{_COMMON_RULES}"
)

TUTORIAL_SUGGEST_CONTEXT = (
    f"What you know:\n{_TOWN_KNOWLEDGE} Your mate Pip runs a training "
    "course for newcomers. The cellar is clear now — this adventurer "
    "handled the rats.\n\n"
    "CURRENT SITUATION: This visitor cleared the cellar but skipped "
    "the tutorial. They might benefit from learning the basics.\n"
    "YOUR GOAL: Casually mention the tutorial — type |wtutorial|n — "
    "as something that might help them with crafting, banking, and "
    "other town systems. Don't be pushy; they've already proven "
    "themselves in combat.\n\n"
    f"{_COMMON_RULES}"
)

GENERIC_CONTEXT = (
    f"What you know:\n{_TOWN_KNOWLEDGE}\n\n"
    "CURRENT SITUATION: This is a regular visitor. No special agenda.\n"
    "YOUR GOAL: Be a friendly, welcoming bartender. Chat about the "
    "town, offer food and drink, share gossip. Just be Rowan.\n\n"
    f"{_COMMON_RULES}"
)


class BartenderNPC(QuestGiverMixin, LLMRoleplayNPC):
    """Quest-aware bartender NPC for the Harvest Moon Inn."""

    llm_prompt_file = AttributeProperty("bartender.md")

    STARTER_LEVEL_CAP = 3

    def _get_context_variables(self):
        context = super()._get_context_variables()
        speaker = getattr(self.ndb, "_llm_current_speaker", None)
        if speaker:
            context["quest_context"] = self._build_quest_context(speaker)
        else:
            context["quest_context"] = GENERIC_CONTEXT
        return context

    def _build_quest_context(self, character):
        """Build state-specific LLM instructions based on player state."""
        quest_key = self.quest_key

        # Warrior guild referral — bypass level gate if sent by guildmaster
        if (getattr(character, "level", 1) >= self.STARTER_LEVEL_CAP
                and hasattr(character, "quests")
                and character.quests.has("warrior_initiation")
                and not character.quests.is_completed("warrior_initiation")):
            has_quest = (
                hasattr(character, "quests")
                and character.quests.has(quest_key)
            ) if quest_key else False
            quest_done = (
                character.quests.is_completed(quest_key) if has_quest else False
            )
            if not has_quest:
                return QUEST_PITCH_CONTEXT
            elif not quest_done:
                return QUEST_ACTIVE_CONTEXT

        # Level gate — experienced players get generic bartender
        if getattr(character, "level", 1) >= self.STARTER_LEVEL_CAP:
            return GENERIC_CONTEXT
        if not quest_key:
            return GENERIC_CONTEXT

        # Check tutorial completion (per-account flag set by tutorial system)
        account = getattr(character, "account", None)
        tutorial_completed = False
        if account:
            tutorial_completed = getattr(
                account.db, "tutorial_starter_given", False
            )

        # Check quest state
        has_quest = hasattr(character, "quests") and character.quests.has(
            quest_key
        )
        quest_done = (
            character.quests.is_completed(quest_key) if has_quest else False
        )
        quest_active = has_quest and not quest_done

        if quest_active:
            return QUEST_ACTIVE_CONTEXT
        elif not tutorial_completed and not has_quest:
            return NEW_PLAYER_CONTEXT
        elif tutorial_completed and not has_quest:
            return QUEST_PITCH_CONTEXT
        elif not tutorial_completed and quest_done:
            return TUTORIAL_SUGGEST_CONTEXT
        else:
            return GENERIC_CONTEXT

    def get_quest_completion_message(self, caller, quest):
        """Rowan-specific quest completion message."""
        return (
            "|g\"Well done! The cellar's clear — I owe you one. "
            "There's always a cold ale waiting for you here.\"|n"
        )

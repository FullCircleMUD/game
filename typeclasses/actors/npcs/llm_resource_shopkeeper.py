"""
LLMResourceShopkeeperNPC — LLM-powered resource shopkeeper.

Combines ``LLMRoleplayNPC`` (personality, memory, speech detection) with
``ResourceShopkeeperNPC`` (shop attrs + AMM trading via ``ResourceShopCmdSet``).
Injects a ``{shop_commands}`` block into the LLM prompt so the model
knows which commands exist and what this shop trades, preventing it from
fake-roleplaying transactions that need to go through the cmd grammar.

NPCs that also give quests compose ``LLMQuestContextMixin`` +
``QuestGiverMixin`` on top:

    class BakerNPC(
        LLMQuestContextMixin,
        QuestGiverMixin,
        LLMResourceShopkeeperNPC,
    ):
        ...

Configuration (set per instance):
    inventory: list of int resource IDs
    shop_name: display name for the shop
    llm_prompt_file: prompt template with {shop_commands}
    llm_personality: character voice and traits
    llm_use_vector_memory: defaults to False (short-term memory only)
"""

from evennia.typeclasses.attributes import AttributeProperty

from blockchain.xrpl.currency_cache import get_resource_type
from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC
from typeclasses.actors.npcs.resource_shopkeeper import ResourceShopkeeperNPC


DEFAULT_SHOP_COMMANDS = [
    ("list", "See what the shop trades"),
    ("quote buy <amount> <item>", "Get a price quote for buying"),
    ("quote sell <amount> <item>", "Get a price quote for selling"),
    ("accept", "Accept a pending price quote"),
    ("buy <amount> <item>", "Buy at the current market price"),
    ("sell <amount> <item>", "Sell at the current market price"),
]


class LLMResourceShopkeeperNPC(LLMRoleplayNPC, ResourceShopkeeperNPC):
    """LLM-powered resource shopkeeper. Use directly, or compose with quest mixins."""

    llm_prompt_file = AttributeProperty("shopkeeper.md")
    llm_use_vector_memory = AttributeProperty(False)

    # Shop commands shown in the LLM prompt — override in subclass if needed
    SHOP_COMMAND_HELP = DEFAULT_SHOP_COMMANDS

    # ── Context variable injection ────────────────────────────────────

    def _get_context_variables(self):
        context = super()._get_context_variables()
        context["shop_commands"] = self._build_shop_commands()
        return context

    def _build_shop_commands(self):
        """Formatted ``{shop_commands}`` block for the LLM prompt.

        Lists the buy/sell/quote command syntax plus what this shop
        trades, so the LLM can accurately direct players to the right
        command rather than fake the interaction in dialogue.
        """
        lines = [
            "SHOP COMMANDS — IMPORTANT: You CANNOT complete transactions through conversation. "
            "You MUST direct players to use these commands. NEVER pretend to sell items through dialogue. "
            "When a player wants to buy or sell, tell them the exact command to type:"
        ]

        for syntax, desc in self.SHOP_COMMAND_HELP:
            lines.append(f"  {syntax} — {desc}")

        tradeable = list(self.inventory or [])
        if tradeable:
            names = []
            for rid in tradeable:
                rt = get_resource_type(rid)
                if rt:
                    names.append(rt["name"])
            if names:
                lines.append(f"\nYou trade: {', '.join(names)}.")
        else:
            lines.append("\nYou have nothing to trade right now.")

        return "\n".join(lines)

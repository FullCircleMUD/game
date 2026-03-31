"""
LLMShopkeeperNPC — LLM-powered NPC with AMM shop commands.

Combines LLMRoleplayNPC (dialogue, memory, speech detection) with
ShopkeeperCmdSet (AMM-driven buy/sell commands). The LLM prompt receives
a {shop_commands} block so the NPC can guide players to trading commands.

For shopkeepers that also give quests, use QuestGivingShopkeeper instead.

Usage (spawn script)::

    npc = create_object(
        "typeclasses.actors.npcs.llm_shopkeeper_npc.LLMShopkeeperNPC",
        key="Big Bjorn",
        location=room,
    )
    npc.tradeable_resources = [6, 7]   # wood, timber
    npc.shop_name = "Bjorn's Lumber Yard"
    npc.llm_personality = "An enormous cheerful lumberjack..."
"""

from evennia.typeclasses.attributes import AttributeProperty

from blockchain.xrpl.currency_cache import get_resource_type
from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC


# ── Default shop command descriptions ────────────────────────────────
DEFAULT_SHOP_COMMANDS = [
    ("|wlist|n", "See what the shop trades"),
    ("|wquote buy <amount> <item>|n", "Get a price quote for buying"),
    ("|wquote sell <amount> <item>|n", "Get a price quote for selling"),
    ("|waccept|n", "Accept a pending price quote"),
    ("|wbuy <amount> <item>|n", "Buy at the current market price"),
    ("|wsell <amount> <item>|n", "Sell at the current market price"),
]


class LLMShopkeeperNPC(LLMRoleplayNPC):
    """
    LLM-powered NPC with AMM shop commands.

    Combines:
    - LLMRoleplayNPC for LLM dialogue (personality, memory, speech detection)
    - ShopkeeperCmdSet for AMM trading commands (list, quote, buy, sell)
    - Shop command descriptions via {shop_commands} template variable

    Configuration (set per instance):
        tradeable_resources: list of int resource IDs this shop trades
        shop_name: display name for the shop
        llm_prompt_file: prompt template with {shop_commands}
        llm_use_vector_memory: defaults to False (short-term memory only)
    """

    # Use the shopkeeper-specific prompt template
    llm_prompt_file = AttributeProperty("shopkeeper.md")

    # Shopkeeper attributes (same as ShopkeeperNPC)
    tradeable_resources = AttributeProperty([])
    shop_name = AttributeProperty("Shop")

    # Default to short-term memory only
    llm_use_vector_memory = AttributeProperty(False)

    # Shop commands shown in the LLM prompt — override in subclass if needed
    SHOP_COMMAND_HELP = DEFAULT_SHOP_COMMANDS

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_shopkeeper import ShopkeeperCmdSet
        self.cmdset.add(ShopkeeperCmdSet, persistent=True)

    # ── Context variable injection ────────────────────────────────────

    def _get_context_variables(self):
        context = super()._get_context_variables()
        context["shop_commands"] = self._build_shop_commands()
        return context

    def _build_shop_commands(self):
        """
        Build a formatted block of shop commands for the LLM prompt.

        Includes the command syntax with color codes and a description,
        plus a list of what this shop trades.
        """
        lines = [
            "SHOP COMMANDS — IMPORTANT: You CANNOT complete transactions through conversation. "
            "You MUST direct players to use these commands. NEVER pretend to sell items through dialogue. "
            "When a player wants to buy or sell, tell them the exact command to type:"
        ]

        for syntax, desc in self.SHOP_COMMAND_HELP:
            lines.append(f"  {syntax} — {desc}")

        # Add what this shop trades
        tradeable = list(self.tradeable_resources or [])
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

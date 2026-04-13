"""
LLMNFTShopkeeperNPC — LLM-powered NFT shopkeeper.

Combines ``LLMRoleplayNPC`` (personality, memory, speech detection) with
``NFTShopkeeperNPC`` (shop attrs + AMM trading via ``NFTShopCmdSet``).
Mirrors ``LLMResourceShopkeeperNPC`` but with NFT-shaped shop commands
(no quantity slot in buy/sell/quote).

No concrete consumer yet, but the scaffold exists so the first LLM NFT
shopkeeper NPC can slot in without touching this file.

Configuration (set per instance):
    inventory: list of NFTItemType name strings
    shop_name: display name for the shop
    llm_prompt_file: prompt template with {shop_commands}
    llm_personality: character voice and traits
    llm_use_vector_memory: defaults to False (short-term memory only)
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC
from typeclasses.actors.npcs.nft_shopkeeper import NFTShopkeeperNPC


DEFAULT_SHOP_COMMANDS = [
    ("list", "See what the shop trades"),
    ("quote buy <item>", "Get a price quote for buying"),
    ("quote sell <item>", "Get a price quote for selling"),
    ("accept", "Accept a pending price quote"),
    ("buy <item>", "Buy at the current market price"),
    ("sell <item>", "Sell at the current market price"),
]


class LLMNFTShopkeeperNPC(LLMRoleplayNPC, NFTShopkeeperNPC):
    """LLM-powered NFT shopkeeper. Use directly, or compose with quest mixins."""

    llm_prompt_file = AttributeProperty("shopkeeper.md")
    llm_use_vector_memory = AttributeProperty(False)

    SHOP_COMMAND_HELP = DEFAULT_SHOP_COMMANDS

    # ── Context variable injection ────────────────────────────────────

    def _get_context_variables(self):
        context = super()._get_context_variables()
        context["shop_commands"] = self._build_shop_commands()
        return context

    def _build_shop_commands(self):
        """Formatted ``{shop_commands}`` block for the LLM prompt.

        NFT variant — no quantities in the syntax, and inventory atoms
        are item type names, not resource IDs.
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
            lines.append(f"\nYou trade: {', '.join(tradeable)}.")
        else:
            lines.append("\nYou have nothing to trade right now.")

        return "\n".join(lines)

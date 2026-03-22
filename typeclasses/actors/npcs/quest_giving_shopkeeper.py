"""
QuestGivingShopkeeper — LLM NPC that doubles as an AMM shopkeeper.

Combines QuestGiverMixin (quest accept/abandon/view/turn-in command),
LLMRoleplayNPC (LLM dialogue with quest-aware context injection), and
ShopkeeperCmdSet (AMM-driven buy/sell commands). The LLM prompt receives
both a {quest_context} block (state-specific instructions) and a
{shop_commands} block (available trading commands with descriptions)
so the NPC can naturally guide players to the right commands.

Subclass this for specific NPCs (e.g. BakerNPC) — override
``_build_quest_context()`` to inject quest-specific state detection,
and ``get_quest_completion_message()`` for custom completion text.

Usage (spawn script)::

    npc = create_object(
        "typeclasses.actors.npcs.quest_giving_shopkeeper.QuestGivingShopkeeper",
        key="Bron",
        location=room,
    )
    npc.tradeable_resources = [2, 3]   # flour, bread
    npc.shop_name = "Goldencrust Bakery"
    npc.quest_key = "bakers_flour"
    npc.llm_prompt_file = "baker.md"
    npc.llm_personality = "A flour-dusted baker..."
"""

from evennia.typeclasses.attributes import AttributeProperty

from blockchain.xrpl.currency_cache import get_resource_type
from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC
from typeclasses.mixins.quest_giver import QuestGiverMixin


# ── Default shop command descriptions ────────────────────────────────
# Each entry: (command_syntax, description).
# These are formatted into the LLM prompt so the NPC can tell players
# what to type. Subclasses can override SHOP_COMMAND_HELP to customise.

DEFAULT_SHOP_COMMANDS = [
    ("|wlist|n", "See what the shop trades"),
    ("|wquote buy <amount> <item>|n", "Get a price quote for buying"),
    ("|wquote sell <amount> <item>|n", "Get a price quote for selling"),
    ("|waccept|n", "Accept a pending price quote"),
    ("|wbuy <amount> <item>|n", "Buy at the current market price"),
    ("|wsell <amount> <item>|n", "Sell at the current market price"),
]


class QuestGivingShopkeeper(QuestGiverMixin, LLMRoleplayNPC):
    """
    LLM-powered NPC with AMM shop commands, quest commands, and quest-aware context.

    Combines:
    - QuestGiverMixin for quest accept/abandon/view/turn-in via ``quest`` command
    - LLMRoleplayNPC for LLM dialogue (personality, memory, speech detection)
    - ShopkeeperCmdSet for AMM trading commands (list, quote, buy, sell)
    - Quest-aware context injection via {quest_context} template variable
    - Shop command descriptions via {shop_commands} template variable

    Configuration (set per instance):
        quest_key: quest key this NPC offers (from QuestGiverMixin)
        tradeable_resources: list of int resource IDs this shop trades
        shop_name: display name for the shop
        llm_prompt_file: prompt template with {quest_context} and {shop_commands}
        llm_use_vector_memory: defaults to False (short-term memory only)

    Subclasses should override ``_build_quest_context()`` to implement
    quest-specific state detection for their NPC, and
    ``get_quest_completion_message()`` for custom completion text.
    """

    # Shopkeeper attributes (same as ShopkeeperNPC)
    tradeable_resources = AttributeProperty([])
    shop_name = AttributeProperty("Shop")

    # Default to short-term memory only
    llm_use_vector_memory = AttributeProperty(False)

    # Level gate — experienced players get generic prompts
    STARTER_LEVEL_CAP = 3

    # Shop commands shown in the LLM prompt — override in subclass if needed
    SHOP_COMMAND_HELP = DEFAULT_SHOP_COMMANDS

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_shopkeeper import ShopkeeperCmdSet
        self.cmdset.add(ShopkeeperCmdSet, persistent=True)

    # ── Context variable injection ────────────────────────────────────

    def _get_context_variables(self):
        context = super()._get_context_variables()

        # Inject quest context based on the current speaker's state
        speaker = getattr(self.ndb, "_llm_current_speaker", None)
        if speaker:
            context["quest_context"] = self._build_quest_context(speaker)
        else:
            context["quest_context"] = ""

        # Inject shop command descriptions
        context["shop_commands"] = self._build_shop_commands()

        return context

    def _build_quest_context(self, character):
        """
        Build state-specific LLM instructions based on the player's state.

        Override this in subclasses to implement NPC-specific quest logic.
        The default returns an empty string (no quest agenda).
        """
        return ""

    def _build_shop_commands(self):
        """
        Build a formatted block of shop commands for the LLM prompt.

        Includes the command syntax with color codes and a description,
        plus a list of what this shop trades.
        """
        lines = ["SHOP COMMANDS (tell players these when they ask about buying or selling):"]

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

"""
ShopkeeperNPC — buys and sells resources via XRPL AMM pools.

Prices are driven by on-chain AMM pools (constant product formula).
Each shopkeeper instance lists the resource IDs it trades. Prices
are live market rates — they change with every trade.

Players interact via commands injected by this NPC's CmdSet:
    list               — show tradeable resources with current prices
    quote buy/sell     — get a price quote for a transaction
    accept             — execute a pending quote
    buy <amount> <item>  — instant buy at current market price
    sell <amount> <item> — instant sell at current market price
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npc import BaseNPC


class ShopkeeperNPC(BaseNPC):
    """
    Shopkeeper — buys and sells resources via AMM pools.

    Configuration (set per instance via @set or prototype):
        tradeable_resources: list of int resource IDs this shop trades
            e.g. [1, 2, 3] for Wheat, Flour, Bread
        shop_name: display name for the shop (e.g. "Baker's Shop")
    """

    tradeable_resources = AttributeProperty([])
    shop_name = AttributeProperty("Shop")

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_shopkeeper import ShopkeeperCmdSet
        self.cmdset.add(ShopkeeperCmdSet, persistent=True)

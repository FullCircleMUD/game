"""
NFTShopkeeperNPC — buys and sells NFT equipment via proxy token AMM pools.

Prices are driven by on-chain AMM pools (PToken/PGold constant product).
Each shopkeeper instance lists the NFTItemType names it trades. Only items
with a non-NULL tracking_token are listed or accepted for trade.

Players interact via commands injected by this NPC's CmdSet:
    list               — show tradeable items with current prices
    quote buy/sell     — get a price quote for an item
    accept             — execute a pending quote
    buy <item>         — instant buy at current market price
    sell <item>        — instant sell at current market price
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npc import BaseNPC


class NFTShopkeeperNPC(BaseNPC):
    """
    Equipment shopkeeper — buys and sells NFT items via proxy token AMM pools.

    Configuration (set per instance via @set or prototype):
        tradeable_item_types: list of str NFTItemType names this shop trades
            e.g. ["Training Dagger", "Training Shortsword"]
        shop_name: display name for the shop (e.g. "Blacksmith")
    """

    tradeable_item_types = AttributeProperty([])
    shop_name = AttributeProperty("Equipment Shop")

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_nft_shopkeeper import NFTShopkeeperCmdSet
        self.cmdset.add(NFTShopkeeperCmdSet, persistent=True)

    def get_tradeable_types(self):
        """
        Return NFTItemType queryset filtered to items with tracking_tokens.

        Developer-proof: even if an item type name is in the configuration
        list but has no tracking_token set, it is silently excluded.
        """
        from blockchain.xrpl.models import NFTItemType
        return NFTItemType.objects.filter(
            name__in=self.tradeable_item_types,
            tracking_token__isnull=False,
        )

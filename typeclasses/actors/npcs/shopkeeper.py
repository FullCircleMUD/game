"""
ShopkeeperNPC — abstract base for all shopkeeper NPCs.

Owns the single source of truth for the shopkeeper contract:

- ``shop_name`` — display name
- ``inventory`` — list of tradeable item keys (atom type defined by subclass)
- Abstract pricing / execution interface

Concrete subclasses (``ResourceShopkeeperNPC``, ``NFTShopkeeperNPC``)
implement the abstract methods against their respective AMM services.
Cmdsets call the abstract methods via ``self.obj.get_buy_price(...)`` etc.
and never reach into service classes directly — that keeps the cmdset
decoupled from which backend is serving prices.

Any NPC that wants shop commands must inherit from this class (directly
or via a concrete subclass). Attaching a shop cmdset to an NPC that does
NOT inherit from ``ShopkeeperNPC`` is unsupported and will fail at
first cache flush when the attribute assignments evaporate.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.npc import BaseNPC


class ShopkeeperNPC(BaseNPC):
    """Abstract shopkeeper base class.

    Subclasses must implement:
        get_buy_price(item_key, qty=1) -> int
        get_sell_price(item_key, qty=1) -> int
        execute_buy(caller, quote) -> dict
        execute_sell(caller, quote) -> dict
        list_inventory() -> list[dict]

    The ``inventory`` attribute is declared here but its element type
    is subclass-defined (``int`` resource_id for resource shops,
    ``str`` NFTItemType name for NFT shops).
    """

    shop_name = AttributeProperty("Shop")
    inventory = AttributeProperty([])

    # ── Abstract pricing interface ──────────────────────────────────

    def get_buy_price(self, item_key, qty=1):
        """Return the integer gold cost to buy ``qty`` of ``item_key``.

        Implementations should ceil-round so any AMM-integer slippage
        stays in the game's favour.
        """
        raise NotImplementedError

    def get_sell_price(self, item_key, qty=1):
        """Return the integer gold received for selling ``qty`` of ``item_key``.

        Implementations should floor-round so any AMM-integer slippage
        stays in the game's favour.
        """
        raise NotImplementedError

    def execute_buy(self, caller, quote):
        """Execute a buy transaction against the normalised ``quote`` dict.

        Quote fields: direction, shopkeeper_dbref, gold_price, item_key,
        qty, display. Implementations are responsible for:

        - Running the on-chain swap (typically via ``deferToThread``).
        - Updating the caller's Evennia state (gold, inventory, worn items).
        - Returning a result dict for the caller message.
        """
        raise NotImplementedError

    def execute_sell(self, caller, quote):
        """Execute a sell transaction against the normalised ``quote`` dict."""
        raise NotImplementedError

    def list_inventory(self):
        """Return a list of ``{name, item_key, buy_price, sell_price}`` dicts.

        Used by ``CmdShopList`` to render the browse output without any
        knowledge of resource vs NFT shops. Prices may be omitted (``None``)
        if the subclass only supplies them at quote time.
        """
        raise NotImplementedError

    def quote_hint(self):
        """Return the hint line shown at the bottom of the ``list`` output.

        Differs per shop type because the grammar is different:
        resources need quantity, NFTs don't.
        """
        raise NotImplementedError

"""
NFTShopkeeperNPC — shopkeeper that trades unique NFT items via AMM proxy pools.

Concrete subclass of ``ShopkeeperNPC``. The ``inventory`` atom is a
``str`` NFTItemType name. Pricing is backed by ``NFTAMMService``, which
queries XRPL AMM pools of the form ``<tracking_token> ⇄ PGold`` (the
per-type proxy fungible shadow). Players pay/receive FCMGold; PGold
and the tracking tokens are vault-internal only.

Commands are attached via ``NFTShopCmdSet`` in ``at_object_creation``.
The cmdset calls ``self.obj.get_buy_price(...)`` / ``execute_buy(...)``
without knowing it's an NFT shop — that polymorphism lives here.

Quantity is structurally forbidden: NFTs are unique, so every quote
has ``qty == 1`` and ``execute_buy``/``execute_sell`` assert it as a
paranoia guard at the typeclass boundary.
"""

from django.conf import settings
from twisted.internet import threads

from blockchain.xrpl.xrpl_tx import XRPLTransactionError
from typeclasses.actors.npcs.shopkeeper import ShopkeeperNPC


def _session_check(caller):
    return caller.sessions.count() > 0


class NFTShopkeeperNPC(ShopkeeperNPC):
    """Shopkeeper that trades unique NFT items via XRPL AMM proxy pools.

    ``inventory`` holds NFTItemType.name strings (inherited shape from
    ``ShopkeeperNPC``; the atom type is enforced by convention, not type
    annotation).
    """

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_nft_shop import NFTShopCmdSet
        self.cmdset.add(NFTShopCmdSet, persistent=True)

    # ── Abstract interface ──────────────────────────────────────────

    def get_buy_price(self, item_key, qty=1):
        """Return the integer (ceil-rounded) gold cost to buy 1 of ``item_key``."""
        assert qty == 1, "NFT shops trade singletons only"
        from blockchain.xrpl.services.nft_amm import NFTAMMService
        tracking_token = self._tracking_token_for(item_key)
        return NFTAMMService.get_buy_price(tracking_token)

    def get_sell_price(self, item_key, qty=1):
        """Return the integer (floor-rounded) gold received for selling 1 of ``item_key``."""
        assert qty == 1, "NFT shops trade singletons only"
        from blockchain.xrpl.services.nft_amm import NFTAMMService
        tracking_token = self._tracking_token_for(item_key)
        return NFTAMMService.get_sell_price(tracking_token)

    def list_inventory(self):
        """Return the inventory as ``[{name, item_key}, ...]``.

        Filters out item types that have no ``tracking_token`` — those
        can't be priced and would break the AMM query path.
        """
        from blockchain.xrpl.models import NFTItemType
        rows = []
        for item_type in NFTItemType.objects.filter(
            name__in=list(self.inventory or []),
            tracking_token__isnull=False,
        ):
            rows.append({"name": item_type.name, "item_key": item_type.name})
        return rows

    def quote_hint(self):
        return (
            "For a price use |wquote buy <item>|n "
            "or |wquote sell <item>|n."
        )

    def get_tradeable_types(self):
        """Return a queryset of NFTItemType rows eligible for trade.

        Back-compat helper used by command-side code (which needs the
        full NFTItemType rows for inventory matching, durability hints,
        etc., not just names).
        """
        from blockchain.xrpl.models import NFTItemType
        return NFTItemType.objects.filter(
            name__in=list(self.inventory or []),
            tracking_token__isnull=False,
        )

    # ── Execution ───────────────────────────────────────────────────

    def execute_buy(self, caller, quote):
        """Execute a buy from a quoted NFT trade.

        Runs the AMM swap in a worker thread, then assigns a blank NFT
        token to the player's inventory and deducts gold on the reactor.
        """
        assert quote.get("qty", 1) == 1, "NFT shops trade singletons only"
        item_type_name = quote["item_key"]
        gold_price = quote["gold_price"]

        if caller.get_gold() < gold_price:
            caller.msg(
                f"You no longer have enough gold. "
                f"Need {gold_price}, have {caller.get_gold()}."
            )
            return

        tracking_token = self._tracking_token_for(item_type_name)

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing trade...|n")
        d = threads.deferToThread(
            _threaded_nft_buy, tracking_token, gold_price,
            caller.get_gold(), wallet, char_key, vault,
        )
        d.addCallback(
            lambda result: self._on_buy_complete(
                caller, item_type_name, gold_price, result,
            )
        )
        d.addErrback(
            lambda f: self._on_trade_error(caller, f, "buy", item_type_name)
        )

    def execute_sell(self, caller, quote):
        """Execute a sell from a quoted NFT trade.

        Uses ``quote['item_dbref']`` to re-locate the specific inventory
        item (NFT sells are per-instance, not per-type).
        """
        assert quote.get("qty", 1) == 1, "NFT shops trade singletons only"
        item_type_name = quote["item_key"]
        gold_price = quote["gold_price"]
        item_dbref = quote.get("item_dbref")

        # Re-validate the specific item still exists in inventory.
        from evennia.objects.models import ObjectDB
        try:
            item = ObjectDB.objects.get(id=item_dbref)
        except ObjectDB.DoesNotExist:
            caller.msg(f"You no longer have that {item_type_name}.")
            return
        if item.location != caller:
            caller.msg(f"You no longer have that {item_type_name}.")
            return

        tracking_token = self._tracking_token_for(item_type_name)

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing trade...|n")
        d = threads.deferToThread(
            _threaded_nft_sell, tracking_token, gold_price,
            wallet, char_key, vault,
        )
        d.addCallback(
            lambda result: self._on_sell_complete(
                caller, item_type_name, item_dbref, gold_price,
            )
        )
        d.addErrback(
            lambda f: self._on_trade_error(caller, f, "sell", item_type_name)
        )

    # ── Result callbacks (reactor thread) ───────────────────────────

    def _on_buy_complete(self, caller, item_type_name, gold_cost, result):
        if not _session_check(caller):
            return
        from typeclasses.items.base_nft_item import BaseNFTItem

        caller._remove_gold(gold_cost)
        token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
        BaseNFTItem.spawn_into(token_id, caller)
        caller.msg(
            f"You buy a {item_type_name} from {self.shop_name} "
            f"for |w{gold_cost} gold|n.\n"
            f"You now have {caller.get_gold()} gold."
        )

    def _on_sell_complete(self, caller, item_type_name, item_dbref, gold_received):
        if not _session_check(caller):
            return
        from evennia.objects.models import ObjectDB

        try:
            item = ObjectDB.objects.get(id=item_dbref)
        except ObjectDB.DoesNotExist:
            caller.msg(
                f"|rTrade failed: you no longer have that {item_type_name}.|n"
            )
            return
        if item.location != caller:
            caller.msg(
                f"|rTrade failed: you no longer have that {item_type_name}.|n"
            )
            return

        # delete() triggers at_object_delete → NFTService returns to RESERVE.
        item.delete()
        caller._add_gold(gold_received)
        caller.msg(
            f"You sell your {item_type_name} to {self.shop_name} "
            f"for |w{gold_received} gold|n.\n"
            f"You now have {caller.get_gold()} gold."
        )

    def _on_trade_error(self, caller, failure, direction, item_type_name):
        if not _session_check(caller):
            return
        error = failure.value
        if isinstance(error, XRPLTransactionError):
            caller.msg(
                f"The market has moved and this trade could not be completed "
                f"({error.result_code}).\n"
                f"Use |wquote {direction} {item_type_name}|n for an updated price."
            )
        elif isinstance(error, ValueError):
            caller.msg(f"|r{error}|n")
        else:
            caller.msg(f"|rTrade failed: {error}|n")

    # ── Helpers ─────────────────────────────────────────────────────

    def _tracking_token_for(self, item_type_name):
        from blockchain.xrpl.models import NFTItemType
        return NFTItemType.objects.get(name=item_type_name).tracking_token


def _threaded_nft_buy(tracking_token, gold_cost, current_gold, wallet,
                       char_key, vault):
    """Worker thread — check blank token availability and execute swap."""
    from blockchain.xrpl.services.nft_amm import NFTAMMService
    from blockchain.xrpl.models import NFTGameState

    blank_count = NFTGameState.objects.filter(
        item_type__isnull=True,
        location=NFTGameState.LOCATION_RESERVE,
    ).count()
    if blank_count == 0:
        raise ValueError("No items available in stock right now.")

    if current_gold < gold_cost:
        raise ValueError(
            f"That costs {gold_cost} gold, but you only have {current_gold}."
        )

    return NFTAMMService.buy_item(
        wallet, char_key, tracking_token, gold_cost, vault,
    )


def _threaded_nft_sell(tracking_token, gold_received, wallet, char_key, vault):
    """Worker thread — execute an NFT sell swap."""
    from blockchain.xrpl.services.nft_amm import NFTAMMService

    if gold_received <= 0:
        raise ValueError(
            "This item's market value is too low to sell right now."
        )

    return NFTAMMService.sell_item(
        wallet, char_key, tracking_token, gold_received, vault,
    )

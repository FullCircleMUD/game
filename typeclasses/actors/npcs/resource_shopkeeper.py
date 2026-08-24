"""
ResourceShopkeeperNPC — shopkeeper that trades fungible resources via AMM pools.

Concrete subclass of ``ShopkeeperNPC``. The ``inventory`` atom is an
``int`` resource ID. Abstract pricing methods are implemented against
``AMMService`` (``blockchain.xrpl.services.amm``), which queries XRPL
AMM pools of the form ``<resource_currency> ⇄ FCMGold``.

Commands are attached via ``ResourceShopCmdSet`` in ``at_object_creation``.
The cmdset calls ``self.obj.get_buy_price(...)`` / ``execute_buy(...)``
without knowing it's a resource shop — that polymorphism lives here.
"""

from django.conf import settings
from django.db import transaction
from twisted.internet import threads

from blockchain.xrpl.currency_cache import get_resource_type
from blockchain.xrpl.xrpl_tx import XRPLTransactionError
from typeclasses.actors.npcs.shopkeeper import ShopkeeperNPC
from utils.attribute_cache import discard_cached_attributes


def _session_check(caller):
    return caller.sessions.count() > 0


class ResourceShopkeeperNPC(ShopkeeperNPC):
    """Shopkeeper that trades fungible resources via XRPL AMM pools."""

    def at_object_creation(self):
        super().at_object_creation()
        from commands.npc_cmds.cmdset_resource_shop import ResourceShopCmdSet
        self.cmdset.add(ResourceShopCmdSet, persistent=True)

    # ── Abstract interface ──────────────────────────────────────────

    def get_buy_price(self, item_key, qty=1):
        """Return the integer (ceil-rounded) gold cost to buy ``qty`` of ``item_key``."""
        from blockchain.xrpl.services.amm import AMMService
        return AMMService.get_buy_price(item_key, qty)

    def get_sell_price(self, item_key, qty=1):
        """Return the integer (floor-rounded) gold received for selling ``qty`` of ``item_key``."""
        from blockchain.xrpl.services.amm import AMMService
        return AMMService.get_sell_price(item_key, qty)

    def list_inventory(self):
        """Return the inventory as ``[{name, item_key}, ...]``.

        Prices are omitted — live market rates are fetched per-quote to
        avoid thundering-herd AMM queries on every ``list``.
        """
        rows = []
        for rid in (self.inventory or []):
            rt = get_resource_type(rid)
            if rt:
                rows.append({"name": rt["name"], "item_key": rid})
        return rows

    def quote_hint(self):
        return (
            "For a price use |wquote buy <amount> <item>|n "
            "or |wquote sell <amount> <item>|n."
        )

    def find_resource(self, name):
        """Case-insensitive lookup of a resource name against inventory.

        Returns ``(resource_id, resource_info_dict)`` or ``(None, None)``.
        """
        name_lower = name.lower().strip()
        for rid in (self.inventory or []):
            rt = get_resource_type(rid)
            if rt and rt["name"].lower() == name_lower:
                return rid, rt
        return None, None

    # ── Execution ───────────────────────────────────────────────────

    def execute_buy(self, caller, quote):
        """Execute a buy from a quoted resource trade.

        Runs the on-chain AMM swap in a worker thread, then updates
        the caller's Evennia state and sends a result message.
        """
        rid = quote["item_key"]
        qty = quote["qty"]
        gold_price = quote["gold_price"]
        display = quote.get("display") or self._display_for(rid, qty)

        # Re-validate funds on the reactor thread before spending.
        if caller.get_gold() < gold_price:
            caller.msg(
                f"You no longer have enough gold. "
                f"Need {gold_price}, have {caller.get_gold()}."
            )
            return

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing trade...|n")
        d = threads.deferToThread(
            _threaded_resource_trade, "buy", wallet, char_key, rid, qty,
            gold_price, vault,
        )
        d.addCallback(
            lambda swap_result: self._on_buy_complete(
                caller, rid, display, qty, gold_price, swap_result,
            )
        )
        d.addErrback(
            lambda f: self._on_trade_error(caller, f, "buy", qty, display)
        )

    def execute_sell(self, caller, quote):
        """Execute a sell from a quoted resource trade."""
        rid = quote["item_key"]
        qty = quote["qty"]
        gold_price = quote["gold_price"]
        display = quote.get("display") or self._display_for(rid, qty)

        if caller.get_resource(rid) < qty:
            caller.msg(
                f"You no longer have enough {display}. "
                f"Need {qty}, have {caller.get_resource(rid)}."
            )
            return

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing trade...|n")
        d = threads.deferToThread(
            _threaded_resource_trade, "sell", wallet, char_key, rid, qty,
            gold_price, vault,
        )
        d.addCallback(
            lambda swap_result: self._on_sell_complete(
                caller, rid, display, qty, gold_price, swap_result,
            )
        )
        d.addErrback(
            lambda f: self._on_trade_error(caller, f, "sell", qty, display)
        )

    # ── Result callbacks (reactor thread) ───────────────────────────

    def _on_buy_complete(self, caller, rid, display, qty, gold_price,
                         swap_result):
        """
        Book a completed buy swap. Runs on the reactor thread.

        The swap has already happened and cannot be undone, so the trade is
        booked whether or not the player is still connected — a disconnect
        mid-trade completes the purchase they asked for rather than voiding
        it. Only the message needs a live session.
        """
        self._record_trade(
            caller, "buy", rid, qty, gold_price, swap_result,
        )
        if not _session_check(caller):
            return
        rt_name = get_resource_type(rid)["name"]
        caller.msg(
            f"You buy {qty} {rt_name} from "
            f"{self.shop_name} for |w{gold_price} gold|n.\n"
            f"You now have {caller.get_gold()} gold "
            f"and {caller.get_resource(rid)} {rt_name}."
        )

    def _on_sell_complete(self, caller, rid, display, qty, gold_price,
                          swap_result):
        """Book a completed sell swap. Runs on the reactor thread."""
        self._record_trade(
            caller, "sell", rid, qty, gold_price, swap_result,
        )
        if not _session_check(caller):
            return
        rt_name = get_resource_type(rid)["name"]
        caller.msg(
            f"You sell {qty} {rt_name} to "
            f"{self.shop_name} for |w{gold_price} gold|n.\n"
            f"You now have {caller.get_gold()} gold "
            f"and {caller.get_resource(rid)} {rt_name}."
        )

    @staticmethod
    def _record_trade(caller, direction, rid, qty, gold_price, swap_result):
        """
        Hold the player's local writes and the ownership write together.

        The swap ran in the worker thread and is outside this transaction —
        one cannot be held open across a ledger round-trip. What is inside
        is the pair that has to agree: what the game says the player holds,
        and what the xrpl database says they own. Local writes go first, so
        a failure in the ownership write takes them with it.

        A swap left unbooked by such a failure is tolerated. It moved assets
        the game already owns between its own vault and its own pool, so the
        only effect is a nudge to the next price.
        """
        from blockchain.xrpl.services.amm import AMMService

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        try:
            with transaction.atomic():
                if direction == "buy":
                    caller._remove_gold(gold_price)
                    caller._add_resource(rid, qty)
                    AMMService.buy_resource_record(
                        wallet, char_key, rid, qty, gold_price, vault,
                        swap_result,
                    )
                else:
                    caller._remove_resource(rid, qty)
                    caller._add_gold(gold_price)
                    AMMService.sell_resource_record(
                        wallet, char_key, rid, qty, gold_price, vault,
                        swap_result,
                    )
        except Exception:
            # The rows are back; the in-memory Attributes are not.
            discard_cached_attributes(caller)
            raise

    def _on_trade_error(self, caller, failure, direction, qty, display):
        if not _session_check(caller):
            return
        error = failure.value
        if isinstance(error, XRPLTransactionError):
            caller.msg(
                f"The market has moved and this trade could not be completed "
                f"({error.result_code}).\n"
                f"Use |wquote {direction} {qty} {display}|n for an updated price."
            )
        elif isinstance(error, ValueError):
            caller.msg(f"|r{error}|n")
        else:
            caller.msg(f"|rTrade failed: {error}|n")

    # ── Helpers ─────────────────────────────────────────────────────

    def _display_for(self, rid, qty):
        rt = get_resource_type(rid)
        return f"{qty} {rt['name']}" if rt else str(rid)


def _threaded_resource_trade(direction, wallet, char_key, rid, qty,
                              gold_price, vault):
    """
    Worker thread — execute the on-chain half of a resource AMM swap.

    The swap only. Booking it happens on the reactor thread, in a
    transaction alongside the player's local writes — see _record_trade().
    Raises on failure rather than returning a status, so a swap that does
    not happen never reaches the callback.
    """
    from blockchain.xrpl.services.amm import AMMService
    if direction == "buy":
        return AMMService.buy_resource_swap(rid, qty, gold_price)
    return AMMService.sell_resource_swap(rid, qty, gold_price)

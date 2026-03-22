"""
Shopkeeper NPC commands — list, quote, accept, buy, sell.

Prices are driven by XRPL AMM pools. Gold amounts are always integers:
buy prices are ceil-rounded (game's favor), sell prices are floor-rounded.
Any favorable slippage between the quoted price and the actual AMM cost
goes to the game as micro-margin.

All XRPL calls run in worker threads (via deferToThread) so the Twisted
reactor stays responsive for other players.

These commands live on the ShopkeeperNPC object's CmdSet. self.obj is the
shopkeeper NPC.
"""

from django.conf import settings
from evennia import CmdSet, Command
from twisted.internet import threads

from blockchain.xrpl.currency_cache import get_resource_type
from blockchain.xrpl.xrpl_tx import XRPLTransactionError


def _find_resource_by_name(name, tradeable_ids):
    """
    Match a resource name against the shopkeeper's tradeable resources.

    Args:
        name: str — player-typed resource name (case-insensitive).
        tradeable_ids: list of int resource IDs.

    Returns:
        (resource_id, resource_info_dict) or (None, None).
    """
    name_lower = name.lower().strip()
    for rid in tradeable_ids:
        rt = get_resource_type(rid)
        if rt and rt["name"].lower() == name_lower:
            return rid, rt
    return None, None


def _parse_amount_and_item(args_str, tradeable_ids, caller=None,
                            allow_all=False, resource_id_for_all=None):
    """
    Parse '<amount> <item>' or 'all <item>' from command args.

    Returns:
        (amount, resource_id, resource_info) or (None, None, None) on error.
        Sends error message to caller if parsing fails.
    """
    parts = args_str.strip().split(None, 1)
    if len(parts) < 2:
        if caller:
            caller.msg("Usage: <amount> <item> (e.g., 10 wheat)")
        return None, None, None

    amount_str, item_name = parts

    # Find the resource
    rid, rt = _find_resource_by_name(item_name, tradeable_ids)
    if rid is None:
        if caller:
            caller.msg(f"This shop doesn't deal in '{item_name}'.")
        return None, None, None

    # Parse amount
    if allow_all and amount_str.lower() == "all":
        if caller:
            amount = caller.get_resource(rid)
            if amount <= 0:
                caller.msg(f"You don't have any {rt['name']}.")
                return None, None, None
        else:
            return None, None, None
    else:
        try:
            amount = int(amount_str)
        except ValueError:
            if caller:
                caller.msg(f"'{amount_str}' is not a valid amount.")
            return None, None, None

    if amount <= 0:
        if caller:
            caller.msg("Amount must be positive.")
        return None, None, None

    return amount, rid, rt


def _session_check(caller):
    """Return True if the caller still has an active session."""
    return caller.sessions.count() > 0


# ── CmdShopList ──────────────────────────────────────────────────────

class CmdShopList(Command):
    """
    List items available at this shop.

    Usage:
        list      — show tradeable items
        browse    — same as list
    """

    key = "list"
    aliases = ["browse"]
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        shop_name = shopkeeper.shop_name or "Shop"
        tradeable = list(shopkeeper.tradeable_resources or [])

        if not tradeable:
            caller.msg(f"|w=== {shop_name} ===|n\nThe shelves are empty.")
            return

        lines = [f"|w=== {shop_name} ===|n"]
        for rid in tradeable:
            rt = get_resource_type(rid)
            if rt:
                lines.append(f"  {rt['name']}")

        lines.append("")
        lines.append(
            "For a price use |wquote buy <amount> <item>|n "
            "or |wquote sell <amount> <item>|n."
        )
        caller.msg("\n".join(lines))


# ── CmdShopQuote ─────────────────────────────────────────────────────

class CmdShopQuote(Command):
    """
    Get a price quote for buying or selling.

    Usage:
        quote buy <amount> <item>     — e.g., quote buy 100 wheat
        quote sell <amount> <item>    — e.g., quote sell 27 flour
        quote sell all <item>         — sell all of a resource

    The quote reflects current market rates and may change due to
    other players' trades. Type 'accept' to proceed at the quoted price.
    """

    key = "quote"
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        tradeable = list(shopkeeper.tradeable_resources or [])
        if not tradeable:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        args = self.args.strip()
        if not args:
            caller.msg(
                "Usage: quote buy <amount> <item> | quote sell <amount> <item>"
            )
            return

        parts = args.split(None, 1)
        direction = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if direction not in ("buy", "sell"):
            caller.msg(
                "Usage: quote buy <amount> <item> | quote sell <amount> <item>"
            )
            return

        allow_all = direction == "sell"
        amount, rid, rt = _parse_amount_and_item(
            rest, tradeable, caller, allow_all=allow_all,
        )
        if amount is None:
            return

        # Pre-validate inventory for sells
        if direction == "sell" and caller.get_resource(rid) < amount:
            caller.msg(
                f"You only have {caller.get_resource(rid)} {rt['name']}."
            )
            return

        caller.msg("|cChecking market price...|n")
        d = threads.deferToThread(_fetch_quote_price, rid, amount, direction)
        d.addCallback(
            lambda price: _on_quote_price(
                caller, shopkeeper, direction, rid, rt, amount, price
            )
        )
        d.addErrback(lambda f: _msg_if_connected(caller, f"|rCannot get price: {f.getErrorMessage()}|n"))


def _fetch_quote_price(rid, amount, direction):
    """Worker thread — get a price quote."""
    from blockchain.xrpl.services.amm import AMMService
    if direction == "buy":
        return AMMService.get_buy_price(rid, amount)
    return AMMService.get_sell_price(rid, amount)


def _on_quote_price(caller, shopkeeper, direction, rid, rt, amount, gold_price):
    """Reactor thread — validate and store quote."""
    if not _session_check(caller):
        return

    if direction == "buy":
        if caller.get_gold() < gold_price:
            caller.msg(
                f"That would cost {gold_price} gold, "
                f"but you only have {caller.get_gold()}."
            )
            return
    else:
        if caller.get_resource(rid) < amount:
            caller.msg(
                f"You only have {caller.get_resource(rid)} {rt['name']}."
            )
            return

    caller.ndb.pending_quote = {
        "type": direction,
        "resource_id": rid,
        "resource_name": rt["name"],
        "amount": amount,
        "gold_price": gold_price,
        "shopkeeper_dbref": shopkeeper.dbref,
    }

    shop_name = shopkeeper.shop_name or shopkeeper.key
    if direction == "buy":
        caller.msg(
            f"{shop_name} will sell you {amount} {rt['name']} "
            f"for |w{gold_price} gold|n.\n"
            f"This price reflects current market rates and may change.\n"
            f"Type |waccept|n to proceed."
        )
    else:
        caller.msg(
            f"{shop_name} will buy your {amount} {rt['name']} "
            f"for |w{gold_price} gold|n.\n"
            f"This price reflects current market rates and may change.\n"
            f"Type |waccept|n to proceed."
        )


# ── CmdShopAccept ────────────────────────────────────────────────────

class CmdShopAccept(Command):
    """
    Accept a pending price quote.

    Usage:
        accept    — execute the last quoted transaction

    You must have a pending quote from the 'quote' command.
    """

    key = "accept"
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        quote = getattr(caller.ndb, "pending_quote", None)
        if not quote:
            caller.msg("You don't have a pending quote. Use |wquote|n first.")
            return

        if quote["shopkeeper_dbref"] != shopkeeper.dbref:
            caller.msg(
                "Your quote was from a different shop. "
                "Use |wquote|n to get a new one here."
            )
            caller.ndb.pending_quote = None
            return

        direction = quote["type"]
        rid = quote["resource_id"]
        amount = quote["amount"]
        gold_price = quote["gold_price"]
        resource_name = quote["resource_name"]

        # Re-validate funds
        if direction == "buy":
            if caller.get_gold() < gold_price:
                caller.msg(
                    f"You no longer have enough gold. "
                    f"Need {gold_price}, have {caller.get_gold()}."
                )
                caller.ndb.pending_quote = None
                return
        else:
            if caller.get_resource(rid) < amount:
                caller.msg(
                    f"You no longer have enough {resource_name}. "
                    f"Need {amount}, have {caller.get_resource(rid)}."
                )
                caller.ndb.pending_quote = None
                return

        # Clear quote before executing
        caller.ndb.pending_quote = None

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing trade...|n")
        d = threads.deferToThread(
            _execute_trade, direction, wallet, char_key, rid, amount,
            gold_price, vault,
        )
        d.addCallback(
            lambda result: _on_trade_complete(
                caller, shopkeeper, direction, rid, resource_name, amount,
                gold_price, result,
            )
        )
        d.addErrback(
            lambda f: _on_trade_error(caller, f, direction, amount, resource_name)
        )


# ── CmdShopBuy ───────────────────────────────────────────────────────

class CmdShopBuy(Command):
    """
    Buy a resource from the shopkeeper at the current market price.

    Usage:
        buy <amount> <item>    — e.g., buy 10 wheat

    Executes immediately at the current AMM price (no quote step).
    For large purchases, use 'quote buy' first to check the price.
    """

    key = "buy"
    aliases = []
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        tradeable = list(shopkeeper.tradeable_resources or [])
        if not tradeable:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        if not self.args.strip():
            caller.msg("Buy what? Usage: buy <amount> <item>")
            return

        amount, rid, rt = _parse_amount_and_item(
            self.args, tradeable, caller,
        )
        if amount is None:
            return

        current_gold = caller.get_gold()
        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing purchase...|n")
        d = threads.deferToThread(
            _threaded_buy, rid, amount, current_gold, wallet, char_key, vault,
        )
        d.addCallback(
            lambda data: _on_trade_complete(
                caller, shopkeeper, "buy", rid, rt["name"], amount,
                data[0], data[1],
            )
        )
        d.addErrback(
            lambda f: _on_trade_error(caller, f, "buy", amount, rt["name"])
        )


def _threaded_buy(rid, amount, current_gold, wallet, char_key, vault):
    """Worker thread — get price then execute swap."""
    from blockchain.xrpl.services.amm import AMMService

    gold_cost = AMMService.get_buy_price(rid, amount)
    if current_gold < gold_cost:
        raise ValueError(
            f"That costs {gold_cost} gold, but you only have {current_gold}."
        )
    result = AMMService.buy_resource(
        wallet, char_key, rid, amount, gold_cost, vault,
    )
    return (gold_cost, result)


# ── CmdShopSell ──────────────────────────────────────────────────────

class CmdShopSell(Command):
    """
    Sell a resource to the shopkeeper at the current market price.

    Usage:
        sell <amount> <item>    — e.g., sell 20 flour
        sell all <item>         — sell your entire stock

    Executes immediately at the current AMM price (no quote step).
    For large sales, use 'quote sell' first to check the price.
    """

    key = "sell"
    aliases = []
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        tradeable = list(shopkeeper.tradeable_resources or [])
        if not tradeable:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        if not self.args.strip():
            caller.msg("Sell what? Usage: sell <amount> <item>")
            return

        amount, rid, rt = _parse_amount_and_item(
            self.args, tradeable, caller, allow_all=True,
        )
        if amount is None:
            return

        if caller.get_resource(rid) < amount:
            caller.msg(
                f"You only have {caller.get_resource(rid)} {rt['name']}."
            )
            return

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing sale...|n")
        d = threads.deferToThread(
            _threaded_sell, rid, amount, wallet, char_key, vault,
        )
        d.addCallback(
            lambda data: _on_trade_complete(
                caller, shopkeeper, "sell", rid, rt["name"], amount,
                data[0], data[1],
            )
        )
        d.addErrback(
            lambda f: _on_trade_error(caller, f, "sell", amount, rt["name"])
        )


def _threaded_sell(rid, amount, wallet, char_key, vault):
    """Worker thread — get price then execute swap."""
    from blockchain.xrpl.services.amm import AMMService

    gold_received = AMMService.get_sell_price(rid, amount)
    if gold_received <= 0:
        raise ValueError("The amount is too small to sell — you'd receive 0 gold.")
    result = AMMService.sell_resource(
        wallet, char_key, rid, amount, gold_received, vault,
    )
    return (gold_received, result)


# ── Shared trade callbacks ───────────────────────────────────────────

def _execute_trade(direction, wallet, char_key, rid, amount, gold_price, vault):
    """Worker thread — execute a quoted trade."""
    from blockchain.xrpl.services.amm import AMMService

    if direction == "buy":
        result = AMMService.buy_resource(
            wallet, char_key, rid, amount, gold_price, vault,
        )
    else:
        result = AMMService.sell_resource(
            wallet, char_key, rid, amount, gold_price, vault,
        )
    return result


def _on_trade_complete(caller, shopkeeper, direction, rid, resource_name,
                       amount, gold_price, result):
    """Reactor thread — update Evennia state and notify player."""
    if not _session_check(caller):
        return

    # Update Evennia attribute cache
    if direction == "buy":
        caller._remove_gold(gold_price)
        caller._add_resource(rid, amount)
        caller.msg(
            f"You buy {amount} {resource_name} from "
            f"{shopkeeper.shop_name} for |w{gold_price} gold|n.\n"
            f"You now have {caller.get_gold()} gold "
            f"and {caller.get_resource(rid)} {resource_name}."
        )
    else:
        caller._remove_resource(rid, amount)
        caller._add_gold(gold_price)
        caller.msg(
            f"You sell {amount} {resource_name} to "
            f"{shopkeeper.shop_name} for |w{gold_price} gold|n.\n"
            f"You now have {caller.get_gold()} gold "
            f"and {caller.get_resource(rid)} {resource_name}."
        )


def _on_trade_error(caller, failure, direction, amount, resource_name):
    """Reactor thread — handle trade failure."""
    if not _session_check(caller):
        return

    error = failure.value
    if isinstance(error, XRPLTransactionError):
        caller.msg(
            f"The market has moved and this trade could not be completed "
            f"({error.result_code}).\n"
            f"Use |wquote {direction} {amount} {resource_name}|n "
            f"for an updated price."
        )
    elif isinstance(error, ValueError):
        caller.msg(f"|r{error}|n")
    else:
        caller.msg(f"|rTrade failed: {error}|n")


def _msg_if_connected(caller, msg):
    """Send a message only if the caller still has an active session."""
    if _session_check(caller):
        caller.msg(msg)


# ── CmdSet ───────────────────────────────────────────────────────────

class ShopkeeperCmdSet(CmdSet):
    """Commands available from a ShopkeeperNPC."""

    key = "ShopkeeperCmdSet"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdShopList())
        self.add(CmdShopQuote())
        self.add(CmdShopAccept())
        self.add(CmdShopBuy())
        self.add(CmdShopSell())

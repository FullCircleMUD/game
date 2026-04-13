"""
Resource shop cmdset — quantity-aware buy/sell/quote commands.

Inherits ``CmdShopList`` + ``CmdShopAccept`` from ``ShopCmdSet``. Adds
resource-specific commands whose grammar includes an ``<amount>`` slot:

    quote buy <amount> <item>
    quote sell <amount> <item>
    buy <amount> <item>
    sell <amount> <item>
    sell all <item>

These commands call abstract methods on ``self.obj`` (a
``ResourceShopkeeperNPC``). The cmdset has no knowledge of which AMM
service backs the prices — the NPC owns that binding.
"""

from evennia import Command
from twisted.internet import threads

from commands.command import FCMCommandMixin
from commands.npc_cmds.cmdset_shop_base import ShopCmdSet, _msg_if_connected, _session_check


def _parse_amount_and_item(args_str, shopkeeper, caller=None, allow_all=False):
    """Parse ``<amount> <item>`` / ``all <item>`` from ``args_str``.

    Returns ``(amount, resource_id, resource_info)`` or ``(None, None, None)``
    on error, sending an error message to ``caller`` if parsing fails.
    """
    parts = args_str.strip().split(None, 1)
    if len(parts) < 2:
        if caller:
            caller.msg("Usage: <amount> <item> (e.g., 10 wheat)")
        return None, None, None

    amount_str, item_name = parts

    rid, rt = shopkeeper.find_resource(item_name)
    if rid is None:
        if caller:
            caller.msg(f"This shop doesn't deal in '{item_name}'.")
        return None, None, None

    if allow_all and amount_str.lower() == "all":
        amount = caller.get_resource(rid) if caller else 0
        if caller and amount <= 0:
            caller.msg(f"You don't have any {rt['name']}.")
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


# ── CmdResourceQuote ─────────────────────────────────────────────────


class CmdResourceQuote(FCMCommandMixin, Command):
    """
    Get a price quote for buying or selling.

    Usage:
        quote buy <amount> <item>     — e.g., quote buy 100 wheat
        quote sell <amount> <item>    — e.g., quote sell 27 flour
        quote sell all <item>         — sell all of a resource
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

        if not shopkeeper.inventory:
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
            rest, shopkeeper, caller, allow_all=allow_all,
        )
        if amount is None:
            return

        if direction == "sell" and caller.get_resource(rid) < amount:
            caller.msg(f"You only have {caller.get_resource(rid)} {rt['name']}.")
            return

        caller.msg("|cChecking market price...|n")
        d = threads.deferToThread(
            _fetch_price, shopkeeper, direction, rid, amount,
        )
        d.addCallback(
            lambda price: _on_quote_price(
                caller, shopkeeper, direction, rid, rt, amount, price,
            )
        )
        d.addErrback(
            lambda f: _msg_if_connected(
                caller, f"|rCannot get price: {f.getErrorMessage()}|n"
            )
        )


def _fetch_price(shopkeeper, direction, rid, amount):
    """Worker thread — call the NPC's abstract price method."""
    if direction == "buy":
        return shopkeeper.get_buy_price(rid, amount)
    return shopkeeper.get_sell_price(rid, amount)


def _on_quote_price(caller, shopkeeper, direction, rid, rt, amount, gold_price):
    """Reactor thread — validate and store quote on caller.ndb."""
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
            caller.msg(f"You only have {caller.get_resource(rid)} {rt['name']}.")
            return

    display = f"{amount} {rt['name']}"
    caller.ndb.pending_quote = {
        "direction": direction,
        "shopkeeper_dbref": shopkeeper.dbref,
        "gold_price": gold_price,
        "item_key": rid,
        "qty": amount,
        "display": display,
    }

    shop_name = shopkeeper.shop_name or shopkeeper.key
    verb = "sell you" if direction == "buy" else "buy your"
    caller.msg(
        f"{shop_name} will {verb} {display} for |w{gold_price} gold|n.\n"
        f"This price reflects current market rates and may change.\n"
        f"Type |waccept|n to proceed."
    )


# ── CmdResourceBuy ───────────────────────────────────────────────────


class CmdResourceBuy(FCMCommandMixin, Command):
    """
    Buy a resource at the current market price (no quote step).

    Usage:
        buy <amount> <item>    — e.g., buy 10 wheat
    """

    key = "buy"
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        if not shopkeeper.inventory:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        if not self.args.strip():
            caller.msg("Buy what? Usage: buy <amount> <item>")
            return

        amount, rid, rt = _parse_amount_and_item(self.args, shopkeeper, caller)
        if amount is None:
            return

        caller.msg("|cChecking market price...|n")
        d = threads.deferToThread(
            shopkeeper.get_buy_price, rid, amount,
        )
        d.addCallback(
            lambda gold_price: _dispatch_instant(
                caller, shopkeeper, "buy", rid, rt, amount, gold_price,
            )
        )
        d.addErrback(
            lambda f: _msg_if_connected(
                caller, f"|rTrade failed: {f.getErrorMessage()}|n"
            )
        )


# ── CmdResourceSell ──────────────────────────────────────────────────


class CmdResourceSell(FCMCommandMixin, Command):
    """
    Sell a resource at the current market price (no quote step).

    Usage:
        sell <amount> <item>    — e.g., sell 20 flour
        sell all <item>         — sell your entire stock
    """

    key = "sell"
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        if not shopkeeper.inventory:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        if not self.args.strip():
            caller.msg("Sell what? Usage: sell <amount> <item>")
            return

        amount, rid, rt = _parse_amount_and_item(
            self.args, shopkeeper, caller, allow_all=True,
        )
        if amount is None:
            return

        if caller.get_resource(rid) < amount:
            caller.msg(f"You only have {caller.get_resource(rid)} {rt['name']}.")
            return

        caller.msg("|cChecking market price...|n")
        d = threads.deferToThread(
            shopkeeper.get_sell_price, rid, amount,
        )
        d.addCallback(
            lambda gold_price: _dispatch_instant(
                caller, shopkeeper, "sell", rid, rt, amount, gold_price,
            )
        )
        d.addErrback(
            lambda f: _msg_if_connected(
                caller, f"|rTrade failed: {f.getErrorMessage()}|n"
            )
        )


def _dispatch_instant(caller, shopkeeper, direction, rid, rt, amount, gold_price):
    """Reactor thread — build an ad-hoc quote and dispatch to execute_buy/sell."""
    if not _session_check(caller):
        return

    if direction == "buy" and caller.get_gold() < gold_price:
        caller.msg(
            f"That costs {gold_price} gold, but you only have {caller.get_gold()}."
        )
        return

    if direction == "sell" and gold_price <= 0:
        caller.msg("The amount is too small to sell — you'd receive 0 gold.")
        return

    quote = {
        "direction": direction,
        "shopkeeper_dbref": shopkeeper.dbref,
        "gold_price": gold_price,
        "item_key": rid,
        "qty": amount,
        "display": f"{amount} {rt['name']}",
    }
    if direction == "buy":
        shopkeeper.execute_buy(caller, quote)
    else:
        shopkeeper.execute_sell(caller, quote)


# ── CmdSet ───────────────────────────────────────────────────────────


class ResourceShopCmdSet(ShopCmdSet):
    """Commands available from a ResourceShopkeeperNPC."""

    key = "ResourceShopCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdResourceQuote())
        self.add(CmdResourceBuy())
        self.add(CmdResourceSell())

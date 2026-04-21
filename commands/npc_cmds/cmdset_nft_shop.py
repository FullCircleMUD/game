"""
NFT shop cmdset — qty-forbidden buy/sell/quote commands.

Inherits ``CmdShopList`` + ``CmdShopAccept`` from ``ShopCmdSet``. Adds
NFT-specific commands whose grammar is ``<item>`` only (no quantity):

    quote buy <item>
    quote sell <item>
    buy <item>
    sell <item>

These commands call abstract methods on ``self.obj`` (an
``NFTShopkeeperNPC``). Caller-side inventory concerns (durability,
worn state, gem inset, ambiguous name matching) stay here because they
touch the caller's game state, not the shop's pricing backend.
"""

from evennia import Command
from twisted.internet import threads

from commands.command import FCMCommandMixin
from commands.npc_cmds.cmdset_shop_base import (
    ShopCmdSet,
    _msg_if_connected,
    _session_check,
)


def _find_item_type_by_name(name, tradeable_types):
    """Exact-then-partial match an item name against a tradeable list.

    Returns an ``NFTItemType``, the string ``"ambiguous"`` for multiple
    partial hits, or ``None`` for no match.
    """
    name_lower = name.lower().strip()
    for it in tradeable_types:
        if it.name.lower() == name_lower:
            return it
    partials = [it for it in tradeable_types if name_lower in it.name.lower()]
    if len(partials) == 1:
        return partials[0]
    if len(partials) > 1:
        return "ambiguous"
    return None


def _find_inventory_item(caller, item_name, tradeable_types):
    """Find an NFT in the caller's inventory eligible for sale at this shop.

    Returns ``(item_obj, item_type)`` or ``(None, None)`` with error
    messages sent to the caller.
    """
    from typeclasses.items.base_nft_item import BaseNFTItem
    from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
    from blockchain.xrpl.models import NFTGameState

    name_lower = item_name.lower().strip()

    # Exact match on inventory items first
    item = None
    for obj in caller.contents:
        if not isinstance(obj, BaseNFTItem):
            continue
        if obj.key.lower() == name_lower:
            item = obj
            break

    if item is None:
        partials = [
            obj for obj in caller.contents
            if isinstance(obj, BaseNFTItem) and name_lower in obj.key.lower()
        ]
        if len(partials) == 1:
            item = partials[0]
        elif len(partials) > 1:
            caller.msg("I'm afraid you'll have to be more specific.")
            return None, None

    if item is None:
        caller.msg(f"You don't have '{item_name}' in your inventory.")
        return None, None

    if not item.token_id:
        caller.msg(f"{item.key} is not a valid NFT item.")
        return None, None

    try:
        nft = NFTGameState.objects.get(nftoken_id=str(item.token_id))
    except NFTGameState.DoesNotExist:
        caller.msg(f"{item.key} has no blockchain record.")
        return None, None

    if not nft.item_type:
        caller.msg(f"{item.key} has no item type assigned.")
        return None, None

    item_type = nft.item_type

    if not item_type.tracking_token:
        caller.msg(f"I don't deal in {item_type.name}.")
        return None, None

    tradeable_names = {t.name for t in tradeable_types}
    if item_type.name not in tradeable_names:
        caller.msg(f"This shop doesn't trade in {item_type.name}.")
        return None, None

    max_dur = getattr(item, "max_durability", 0) or 0
    cur_dur = getattr(item, "durability", None)
    if cur_dur is None:
        cur_dur = max_dur
    if max_dur > 0 and cur_dur < max_dur:
        caller.msg(
            f"I don't buy damaged goods. Repair your "
            f"{item_type.name} first. ({cur_dur}/{max_dur} durability)"
        )
        return None, None

    if isinstance(item, WeaponNFTItem) and item.is_inset:
        caller.msg(
            f"That {item_type.name} has been modified with a gem inset. "
            f"I can't price bespoke items — try the auction house."
        )
        return None, None

    if hasattr(caller, "is_worn") and caller.is_worn(item):
        caller.msg(f"Remove {item.key} before selling it.")
        return None, None

    return item, item_type


# ── CmdNFTQuote ──────────────────────────────────────────────────────


class CmdNFTQuote(FCMCommandMixin, Command):
    """
    Get a price quote for buying or selling an item.

    Usage:
        quote buy <item>     — e.g., quote buy training dagger
        quote sell <item>    — e.g., quote sell training dagger
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

        tradeable = list(shopkeeper.get_tradeable_types())
        if not tradeable:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        args = self.args.strip()
        if not args:
            caller.msg("Usage: quote buy <item> | quote sell <item>")
            return

        parts = args.split(None, 1)
        direction = parts[0].lower()
        item_name = parts[1].strip() if len(parts) > 1 else ""

        if direction not in ("buy", "sell"):
            caller.msg("Usage: quote buy <item> | quote sell <item>")
            return

        if not item_name:
            caller.msg(f"Quote {direction} what?")
            return

        if direction == "buy":
            item_type = _find_item_type_by_name(item_name, tradeable)
            if item_type == "ambiguous":
                caller.msg("I'm afraid you'll have to be more specific.")
                return
            if not item_type:
                caller.msg(f"This shop doesn't deal in '{item_name}'.")
                return

            caller.msg("|cChecking market price...|n")
            d = threads.deferToThread(shopkeeper.get_buy_price, item_type.name, 1)
            d.addCallback(
                lambda price: _on_quote_price(
                    caller, shopkeeper, "buy", item_type, None, price,
                )
            )
            d.addErrback(
                lambda f: _msg_if_connected(
                    caller, f"|rCannot get price: {f.getErrorMessage()}|n"
                )
            )
        else:
            item, item_type = _find_inventory_item(caller, item_name, tradeable)
            if item is None:
                return

            caller.msg("|cChecking market price...|n")
            d = threads.deferToThread(shopkeeper.get_sell_price, item_type.name, 1)
            d.addCallback(
                lambda price: _on_quote_price(
                    caller, shopkeeper, "sell", item_type, item, price,
                )
            )
            d.addErrback(
                lambda f: _msg_if_connected(
                    caller, f"|rCannot get price: {f.getErrorMessage()}|n"
                )
            )


def _on_quote_price(caller, shopkeeper, direction, item_type, item, gold_price):
    """Reactor thread — validate and store quote on caller.ndb."""
    if not _session_check(caller):
        return

    if direction == "buy" and caller.get_gold() < gold_price:
        caller.msg(
            f"That would cost {gold_price} gold, "
            f"but you only have {caller.get_gold()}."
        )
        return

    caller.ndb.pending_quote = {
        "direction": direction,
        "shopkeeper_dbref": shopkeeper.dbref,
        "gold_price": gold_price,
        "item_key": item_type.name,
        "qty": 1,
        "display": item_type.name,
        "item_dbref": item.id if item else None,
    }

    shop_name = shopkeeper.shop_name or shopkeeper.key
    verb = "sell you a" if direction == "buy" else "buy your"
    caller.msg(
        f"{shop_name} will {verb} {item_type.name} for |w{gold_price} gold|n.\n"
        f"This price reflects current market rates and may change.\n"
        f"Type |waccept|n to proceed."
    )


# ── CmdNFTBuy ────────────────────────────────────────────────────────


class CmdNFTBuy(FCMCommandMixin, Command):
    """
    Buy an item at the current market price (no quote step).

    Usage:
        buy <item>    — e.g., buy training dagger
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

        tradeable = list(shopkeeper.get_tradeable_types())
        if not tradeable:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        if not self.args.strip():
            caller.msg("Buy what? Usage: buy <item>")
            return

        item_type = _find_item_type_by_name(self.args.strip(), tradeable)
        if item_type == "ambiguous":
            caller.msg("I'm afraid you'll have to be more specific.")
            return
        if not item_type:
            caller.msg(f"This shop doesn't deal in '{self.args.strip()}'.")
            return

        caller.msg("|cChecking market price...|n")
        d = threads.deferToThread(shopkeeper.get_buy_price, item_type.name, 1)
        d.addCallback(
            lambda gold_price: _dispatch_instant(
                caller, shopkeeper, "buy", item_type, None, gold_price,
            )
        )
        d.addErrback(
            lambda f: _msg_if_connected(
                caller, f"|rTrade failed: {f.getErrorMessage()}|n"
            )
        )


# ── CmdNFTSell ───────────────────────────────────────────────────────


class CmdNFTSell(FCMCommandMixin, Command):
    """
    Sell an item at the current market price (no quote step).

    Usage:
        sell <item>    — e.g., sell training dagger

    The item must be at full durability and not gem-inset.
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

        tradeable = list(shopkeeper.get_tradeable_types())
        if not tradeable:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        if not self.args.strip():
            caller.msg("Sell what? Usage: sell <item>")
            return

        item, item_type = _find_inventory_item(
            caller, self.args.strip(), tradeable,
        )
        if item is None:
            return

        caller.msg("|cChecking market price...|n")
        d = threads.deferToThread(shopkeeper.get_sell_price, item_type.name, 1)
        d.addCallback(
            lambda gold_price: _dispatch_instant(
                caller, shopkeeper, "sell", item_type, item, gold_price,
            )
        )
        d.addErrback(
            lambda f: _msg_if_connected(
                caller, f"|rTrade failed: {f.getErrorMessage()}|n"
            )
        )


def _dispatch_instant(caller, shopkeeper, direction, item_type, item, gold_price):
    """Reactor thread — build ad-hoc quote and dispatch to execute_*."""
    if not _session_check(caller):
        return

    if direction == "buy" and caller.get_gold() < gold_price:
        caller.msg(
            f"That costs {gold_price} gold, but you only have {caller.get_gold()}."
        )
        return

    quote = {
        "direction": direction,
        "shopkeeper_dbref": shopkeeper.dbref,
        "gold_price": gold_price,
        "item_key": item_type.name,
        "qty": 1,
        "display": item_type.name,
        "item_dbref": item.id if item else None,
    }
    if direction == "buy":
        shopkeeper.execute_buy(caller, quote)
    else:
        shopkeeper.execute_sell(caller, quote)


# ── CmdSet ───────────────────────────────────────────────────────────


class NFTShopCmdSet(ShopCmdSet):
    """Commands available from an NFTShopkeeperNPC."""

    key = "NFTShopCmdSet"

    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        self.add(CmdNFTQuote())
        self.add(CmdNFTBuy())
        self.add(CmdNFTSell())

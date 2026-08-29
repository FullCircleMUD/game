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
from utils.db_threads import defer_to_db_thread

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


def _match_by_name(candidates, item_name):
    """Return the members of ``candidates`` matching ``item_name``.

    Exact key matches win outright; only when there are none does the
    partial match run.
    """
    name_lower = item_name.lower().strip()
    exact = [obj for obj in candidates if obj.key.lower() == name_lower]
    if exact:
        return exact
    return [obj for obj in candidates if name_lower in obj.key.lower()]


def _check_sellable(item, tradeable_names):
    """Judge one item against every gate the shop applies to a sale.

    Returns ``(item_type, None)`` when the item can be sold here, or
    ``(None, refusal_message)`` for the first gate it fails.
    """
    from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
    from blockchain.xrpl.models import NFTGameState

    if not item.token_id:
        return None, f"{item.key} is not a valid NFT item."

    try:
        nft = NFTGameState.objects.get(nftoken_id=str(item.token_id))
    except NFTGameState.DoesNotExist:
        return None, f"{item.key} has no blockchain record."

    if not nft.item_type:
        return None, f"{item.key} has no item type assigned."

    item_type = nft.item_type

    if not item_type.tracking_token:
        return None, f"I don't deal in {item_type.name}."

    if item_type.name not in tradeable_names:
        return None, f"This shop doesn't trade in {item_type.name}."

    max_dur = getattr(item, "max_durability", 0) or 0
    cur_dur = getattr(item, "durability", None)
    if cur_dur is None:
        cur_dur = max_dur
    if max_dur > 0 and cur_dur < max_dur:
        return None, (
            f"I don't buy damaged goods. Repair your "
            f"{item_type.name} first. ({cur_dur}/{max_dur} durability)"
        )

    if isinstance(item, WeaponNFTItem) and item.is_inset:
        return None, (
            f"That {item_type.name} has been modified with a gem inset. "
            f"I can't price bespoke items — try the auction house."
        )

    return item_type, None


def _find_inventory_item(caller, item_name, tradeable_types):
    """Find an NFT in the caller's inventory eligible for sale at this shop.

    Three steps, in order:

    1. **Name.** Matched against carried items only. Worn gear is not a
       candidate, so it can neither be sold nor shadow a carried item
       that shares its name. Worn items are matched separately, purely
       to phrase the refusal when nothing carried matches.
    2. **Ambiguity.** Decided on the name alone. Two identical pairs of
       pants are one answer, not a question; corduroy pants beside
       leather pants are a question.
    3. **Condition.** Among the copies sharing that name, take one the
       shop will actually buy. The refusal — damaged, gem-inset, not
       stocked here — surfaces only when no copy passes.

    Returns ``(item_obj, item_type)`` or ``(None, None)`` with error
    messages sent to the caller.
    """
    from typeclasses.items.base_nft_item import BaseNFTItem

    can_check_worn = hasattr(caller, "is_worn")

    def is_worn(obj):
        return can_check_worn and caller.is_worn(obj)

    nfts = [obj for obj in caller.contents if isinstance(obj, BaseNFTItem)]
    matches = _match_by_name([obj for obj in nfts if not is_worn(obj)], item_name)

    if not matches:
        worn = _match_by_name([obj for obj in nfts if is_worn(obj)], item_name)
        if worn:
            caller.msg(f"Remove {worn[0].key} before selling it.")
        else:
            caller.msg(f"You don't have '{item_name}' in your inventory.")
        return None, None

    if len({obj.key.lower() for obj in matches}) > 1:
        caller.msg("I'm afraid you'll have to be more specific.")
        return None, None

    tradeable_names = {t.name for t in tradeable_types}
    first_refusal = None
    for obj in matches:
        item_type, refusal = _check_sellable(obj, tradeable_names)
        if item_type is not None:
            return obj, item_type
        if first_refusal is None:
            first_refusal = refusal

    caller.msg(first_refusal)
    return None, None


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
            d = defer_to_db_thread(shopkeeper.get_buy_price, item_type.name, 1)
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
            d = defer_to_db_thread(shopkeeper.get_sell_price, item_type.name, 1)
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
        d = defer_to_db_thread(shopkeeper.get_buy_price, item_type.name, 1)
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
        d = defer_to_db_thread(shopkeeper.get_sell_price, item_type.name, 1)
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

"""
NFT Shopkeeper NPC commands — list, quote, accept, buy, sell.

Prices are driven by XRPL AMM pools using proxy tokens (PToken/PGold).
Players pay/receive FCMGold — proxy tokens are vault-internal only.

All XRPL calls run in worker threads (via deferToThread) so the Twisted
reactor stays responsive for other players.

These commands live on the NFTShopkeeperNPC object's CmdSet. self.obj is
the shopkeeper NPC.
"""

from django.conf import settings
from evennia import CmdSet, Command
from twisted.internet import threads

from blockchain.xrpl.xrpl_tx import XRPLTransactionError


def _session_check(caller):
    """Return True if the caller still has an active session."""
    return caller.sessions.count() > 0


def _msg_if_connected(caller, msg):
    """Send a message only if the caller still has an active session."""
    if _session_check(caller):
        caller.msg(msg)


def _find_item_type_by_name(name, tradeable_types):
    """
    Match an item name against the shopkeeper's tradeable item types.

    Supports exact, starts-with, and substring matching (case-insensitive).
    Priority: exact match > single partial match. If multiple partial
    matches, returns None (ambiguous).

    Args:
        name: str — player-typed item name (case-insensitive).
        tradeable_types: queryset/list of NFTItemType objects.

    Returns:
        NFTItemType or None.
    """
    name_lower = name.lower().strip()

    # Exact match first
    for it in tradeable_types:
        if it.name.lower() == name_lower:
            return it

    # Partial match — collect all that contain the search term
    partials = [it for it in tradeable_types if name_lower in it.name.lower()]

    if len(partials) == 1:
        return partials[0]

    if len(partials) > 1:
        return "ambiguous"

    return None


def _find_inventory_item(caller, item_name, tradeable_types):
    """
    Find an NFT item in the caller's inventory matching the name and
    eligible for trade at this shopkeeper.

    Returns:
        (item_obj, item_type) or (None, None) with error messages sent.
    """
    from typeclasses.items.base_nft_item import BaseNFTItem
    from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
    from blockchain.xrpl.models import NFTItemType

    name_lower = item_name.lower().strip()

    # Search inventory for matching item (exact, then partial)
    item = None
    for obj in caller.contents:
        if not isinstance(obj, BaseNFTItem):
            continue
        if obj.key.lower() == name_lower:
            item = obj
            break

    if item is None:
        # Try partial match
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

    # Look up the item's NFTItemType
    from blockchain.xrpl.models import NFTGameState
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

    # Check it's in this shopkeeper's list
    tradeable_names = {t.name for t in tradeable_types}
    if item_type.name not in tradeable_names:
        caller.msg(f"This shop doesn't trade in {item_type.name}.")
        return None, None

    # Durability check
    max_dur = getattr(item, "max_durability", 0)
    cur_dur = getattr(item, "durability", 0)
    if max_dur > 0 and cur_dur < max_dur:
        caller.msg(
            f"I don't buy damaged goods. Repair your "
            f"{item_type.name} first. "
            f"({cur_dur}/{max_dur} durability)"
        )
        return None, None

    # Inset check (weapons only)
    if isinstance(item, WeaponNFTItem) and item.is_inset:
        caller.msg(
            f"That {item_type.name} has been modified with a gem inset. "
            f"I can't price bespoke items — try the auction house."
        )
        return None, None

    # Check item isn't worn/wielded
    if hasattr(caller, "is_worn") and caller.is_worn(item):
        caller.msg(f"Remove {item.key} before selling it.")
        return None, None

    return item, item_type


# ── CmdNFTShopList ──────────────────────────────────────────────────

class CmdNFTShopList(Command):
    """
    List equipment available at this shop.

    Usage:
        list      — show tradeable items with prices
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

        shop_name = shopkeeper.shop_name or "Equipment Shop"
        tradeable = list(shopkeeper.get_tradeable_types())

        if not tradeable:
            caller.msg(f"|w=== {shop_name} ===|n\nThe racks are empty.")
            return

        lines = [f"|w=== {shop_name} ===|n"]
        for it in tradeable:
            lines.append(f"  {it.name}")

        lines.append("")
        lines.append(
            "For a price use |wquote buy <item>|n "
            "or |wquote sell <item>|n."
        )
        caller.msg("\n".join(lines))


# ── CmdNFTShopQuote ─────────────────────────────────────────────────

class CmdNFTShopQuote(Command):
    """
    Get a price quote for buying or selling an item.

    Usage:
        quote buy <item>     — e.g., quote buy training dagger
        quote sell <item>    — e.g., quote sell training dagger

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

        tradeable = list(shopkeeper.get_tradeable_types())
        if not tradeable:
            caller.msg(f"{shopkeeper.key} has nothing to trade.")
            return

        args = self.args.strip()
        if not args:
            caller.msg(
                "Usage: quote buy <item> | quote sell <item>"
            )
            return

        parts = args.split(None, 1)
        direction = parts[0].lower()
        item_name = parts[1].strip() if len(parts) > 1 else ""

        if direction not in ("buy", "sell"):
            caller.msg(
                "Usage: quote buy <item> | quote sell <item>"
            )
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
            d = threads.deferToThread(
                _fetch_nft_quote_price, item_type.tracking_token, "buy",
            )
            d.addCallback(
                lambda price: _on_nft_quote_price(
                    caller, shopkeeper, "buy", item_type, None, price,
                )
            )
            d.addErrback(
                lambda f: _msg_if_connected(
                    caller, f"|rCannot get price: {f.getErrorMessage()}|n"
                )
            )

        else:  # sell
            item, item_type = _find_inventory_item(
                caller, item_name, tradeable,
            )
            if item is None:
                return

            caller.msg("|cChecking market price...|n")
            d = threads.deferToThread(
                _fetch_nft_quote_price, item_type.tracking_token, "sell",
            )
            d.addCallback(
                lambda price: _on_nft_quote_price(
                    caller, shopkeeper, "sell", item_type, item, price,
                )
            )
            d.addErrback(
                lambda f: _msg_if_connected(
                    caller, f"|rCannot get price: {f.getErrorMessage()}|n"
                )
            )


def _fetch_nft_quote_price(tracking_token, direction):
    """Worker thread — get an NFT AMM price quote."""
    from blockchain.xrpl.services.nft_amm import NFTAMMService
    if direction == "buy":
        return NFTAMMService.get_buy_price(tracking_token)
    return NFTAMMService.get_sell_price(tracking_token)


def _on_nft_quote_price(caller, shopkeeper, direction, item_type, item,
                        gold_price):
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
    # For sells, item was already validated in func()

    caller.ndb.pending_nft_quote = {
        "type": direction,
        "item_type_name": item_type.name,
        "tracking_token": item_type.tracking_token,
        "gold_price": gold_price,
        "shopkeeper_dbref": shopkeeper.dbref,
        "item_dbref": item.dbref if item else None,
    }

    shop_name = shopkeeper.shop_name or shopkeeper.key
    if direction == "buy":
        caller.msg(
            f"{shop_name} will sell you a {item_type.name} "
            f"for |w{gold_price} gold|n.\n"
            f"This price reflects current market rates and may change.\n"
            f"Type |waccept|n to proceed."
        )
    else:
        caller.msg(
            f"{shop_name} will buy your {item_type.name} "
            f"for |w{gold_price} gold|n.\n"
            f"This price reflects current market rates and may change.\n"
            f"Type |waccept|n to proceed."
        )


# ── CmdNFTShopAccept ────────────────────────────────────────────────

class CmdNFTShopAccept(Command):
    """
    Accept a pending price quote.

    Usage:
        accept    — execute the last quoted transaction
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

        quote = getattr(caller.ndb, "pending_nft_quote", None)
        if not quote:
            caller.msg(
                "You don't have a pending quote. Use |wquote|n first."
            )
            return

        if quote["shopkeeper_dbref"] != shopkeeper.dbref:
            caller.msg(
                "Your quote was from a different shop. "
                "Use |wquote|n to get a new one here."
            )
            caller.ndb.pending_nft_quote = None
            return

        direction = quote["type"]
        tracking_token = quote["tracking_token"]
        item_type_name = quote["item_type_name"]
        gold_price = quote["gold_price"]
        item_dbref = quote.get("item_dbref")

        # Re-validate
        if direction == "buy":
            if caller.get_gold() < gold_price:
                caller.msg(
                    f"You no longer have enough gold. "
                    f"Need {gold_price}, have {caller.get_gold()}."
                )
                caller.ndb.pending_nft_quote = None
                return
        else:
            # Re-validate the item is still in inventory
            from evennia.objects.models import ObjectDB
            try:
                item = ObjectDB.objects.get(id=item_dbref)
            except ObjectDB.DoesNotExist:
                caller.msg(
                    f"You no longer have that {item_type_name}."
                )
                caller.ndb.pending_nft_quote = None
                return
            if item.location != caller:
                caller.msg(
                    f"You no longer have that {item_type_name}."
                )
                caller.ndb.pending_nft_quote = None
                return

        # Clear quote before executing
        caller.ndb.pending_nft_quote = None

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing trade...|n")

        if direction == "buy":
            d = threads.deferToThread(
                _threaded_nft_buy, tracking_token, gold_price,
                caller.get_gold(), wallet, char_key, vault,
                item_type_name,
            )
            d.addCallback(
                lambda result: _on_nft_buy_complete(
                    caller, shopkeeper, item_type_name, gold_price, result,
                )
            )
            d.addErrback(
                lambda f: _on_nft_trade_error(
                    caller, f, "buy", item_type_name,
                )
            )
        else:
            d = threads.deferToThread(
                _threaded_nft_sell, tracking_token, gold_price,
                wallet, char_key, vault,
            )
            d.addCallback(
                lambda result: _on_nft_sell_complete(
                    caller, shopkeeper, item_type_name, item_dbref,
                    gold_price, result,
                )
            )
            d.addErrback(
                lambda f: _on_nft_trade_error(
                    caller, f, "sell", item_type_name,
                )
            )


# ── CmdNFTShopBuy ───────────────────────────────────────────────────

class CmdNFTShopBuy(Command):
    """
    Buy an item from the shopkeeper at the current market price.

    Usage:
        buy <item>    — e.g., buy training dagger

    Executes immediately at the current AMM price (no quote step).
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

        current_gold = caller.get_gold()
        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing purchase...|n")
        d = threads.deferToThread(
            _threaded_nft_buy, item_type.tracking_token, None,
            current_gold, wallet, char_key, vault, item_type.name,
        )
        d.addCallback(
            lambda result: _on_nft_buy_complete(
                caller, shopkeeper, item_type.name,
                result["gold_cost"], result,
            )
        )
        d.addErrback(
            lambda f: _on_nft_trade_error(
                caller, f, "buy", item_type.name,
            )
        )


# ── CmdNFTShopSell ──────────────────────────────────────────────────

class CmdNFTShopSell(Command):
    """
    Sell an item to the shopkeeper at the current market price.

    Usage:
        sell <item>    — e.g., sell training dagger

    Executes immediately at the current AMM price (no quote step).
    The item must be at full durability and not gem-inset.
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

        wallet = caller._get_wallet()
        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS

        caller.msg("|cProcessing sale...|n")
        d = threads.deferToThread(
            _threaded_nft_sell, item_type.tracking_token, None,
            wallet, char_key, vault,
        )
        d.addCallback(
            lambda result: _on_nft_sell_complete(
                caller, shopkeeper, item_type.name, item.dbref,
                result["gold_received"], result,
            )
        )
        d.addErrback(
            lambda f: _on_nft_trade_error(
                caller, f, "sell", item_type.name,
            )
        )


# ── Worker thread functions ─────────────────────────────────────────

def _threaded_nft_buy(tracking_token, quoted_price, current_gold,
                      wallet, char_key, vault, item_type_name):
    """
    Worker thread — check blank token availability, get price, execute swap.
    """
    from blockchain.xrpl.services.nft_amm import NFTAMMService
    from blockchain.xrpl.models import NFTGameState

    # Pre-check: blank tokens available?
    blank_count = NFTGameState.objects.filter(
        item_type__isnull=True,
        location=NFTGameState.LOCATION_RESERVE,
    ).count()
    if blank_count == 0:
        raise ValueError("No items available in stock right now.")

    # Get price (use quoted if provided, otherwise fetch live)
    if quoted_price is not None:
        gold_cost = quoted_price
    else:
        gold_cost = NFTAMMService.get_buy_price(tracking_token)

    if current_gold < gold_cost:
        raise ValueError(
            f"That costs {gold_cost} gold, but you only have {current_gold}."
        )

    result = NFTAMMService.buy_item(
        wallet, char_key, tracking_token, gold_cost, vault,
    )
    return result


def _threaded_nft_sell(tracking_token, quoted_price, wallet, char_key,
                       vault):
    """Worker thread — get price then execute swap."""
    from blockchain.xrpl.services.nft_amm import NFTAMMService

    if quoted_price is not None:
        gold_received = quoted_price
    else:
        gold_received = NFTAMMService.get_sell_price(tracking_token)

    if gold_received <= 0:
        raise ValueError(
            "This item's market value is too low to sell right now."
        )

    result = NFTAMMService.sell_item(
        wallet, char_key, tracking_token, gold_received, vault,
    )
    return result


# ── Reactor thread callbacks ────────────────────────────────────────

def _on_nft_buy_complete(caller, shopkeeper, item_type_name, gold_cost,
                         result):
    """Reactor thread — deduct gold, spawn item, notify player."""
    if not _session_check(caller):
        return

    from typeclasses.items.base_nft_item import BaseNFTItem

    # Deduct gold from Evennia cache
    caller._remove_gold(gold_cost)

    # Assign a blank token and spawn into player inventory
    token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
    obj = BaseNFTItem.spawn_into(token_id, caller)

    shop_name = shopkeeper.shop_name or shopkeeper.key
    caller.msg(
        f"You buy a {item_type_name} from {shop_name} "
        f"for |w{gold_cost} gold|n.\n"
        f"You now have {caller.get_gold()} gold."
    )


def _on_nft_sell_complete(caller, shopkeeper, item_type_name, item_dbref,
                          gold_received, result):
    """Reactor thread — delete item, add gold, notify player."""
    if not _session_check(caller):
        return

    from evennia.objects.models import ObjectDB

    # Re-validate item still exists in inventory
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

    # Delete item (triggers at_object_delete → NFTService returns to RESERVE)
    item.delete()

    # Add gold to Evennia cache
    caller._add_gold(gold_received)

    shop_name = shopkeeper.shop_name or shopkeeper.key
    caller.msg(
        f"You sell your {item_type_name} to {shop_name} "
        f"for |w{gold_received} gold|n.\n"
        f"You now have {caller.get_gold()} gold."
    )


def _on_nft_trade_error(caller, failure, direction, item_type_name):
    """Reactor thread — handle trade failure."""
    if not _session_check(caller):
        return

    error = failure.value
    if isinstance(error, XRPLTransactionError):
        caller.msg(
            f"The market has moved and this trade could not be completed "
            f"({error.result_code}).\n"
            f"Use |wquote {direction} {item_type_name}|n "
            f"for an updated price."
        )
    elif isinstance(error, ValueError):
        caller.msg(f"|r{error}|n")
    else:
        caller.msg(f"|rTrade failed: {error}|n")


# ── CmdSet ──────────────────────────────────────────────────────────

class NFTShopkeeperCmdSet(CmdSet):
    """Commands available from an NFTShopkeeperNPC."""

    key = "NFTShopkeeperCmdSet"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdNFTShopList())
        self.add(CmdNFTShopQuote())
        self.add(CmdNFTShopAccept())
        self.add(CmdNFTShopBuy())
        self.add(CmdNFTShopSell())

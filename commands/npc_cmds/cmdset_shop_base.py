"""
Shop cmdset base — shared commands for any ShopkeeperNPC subclass.

Owns ``list``/``browse`` and ``accept``. These commands are shop-type
agnostic: they call abstract methods on ``self.obj`` (the NPC) and never
touch service classes directly. Resource vs NFT polymorphism lives
entirely inside the NPC subclasses' ``list_inventory`` / ``execute_buy``
/ ``execute_sell`` implementations.

The resource and NFT cmdsets inherit from ``ShopCmdSet`` and add their
own ``buy``/``sell``/``quote`` commands whose grammar differs (quantity
is mandatory for resources, forbidden for NFTs).

Quote payload shape (stored on ``caller.ndb.pending_quote``):

    {
        "direction": "buy" | "sell",
        "shopkeeper_dbref": str,   # staleness check
        "gold_price": int,         # ceil for buy, floor for sell
        "item_key": int | str,     # resource_id or NFTItemType.name
        "qty": int,                # always 1 for NFT, >=1 for resources
        "display": str,            # "5 timber" or "Training Dagger"
    }

``CmdShopAccept`` validates direction + dbref staleness + gold balance
and then calls ``shopkeeper.execute_buy(caller, quote)`` /
``execute_sell(caller, quote)`` — the subclass unpacks ``item_key``
and ``qty`` however it wants.
"""

from evennia import CmdSet, Command

from commands.command import FCMCommandMixin


def _session_check(caller):
    """True if the caller still has an active session."""
    return caller.sessions.count() > 0


def _msg_if_connected(caller, msg):
    """Send ``msg`` only if the caller still has an active session."""
    if _session_check(caller):
        caller.msg(msg)


# ── CmdShopList ──────────────────────────────────────────────────────


class CmdShopList(FCMCommandMixin, Command):
    """
    List items available at this shop.

    Usage:
        list      — show tradeable items
        browse    — same as list
    """

    key = "list"
    aliases = []
    locks = "cmd:all()"
    help_category = "Shopping"

    def func(self):
        caller = self.caller
        shopkeeper = self.obj

        if shopkeeper.location != caller.location:
            caller.msg("There is no shopkeeper here.")
            return

        shop_name = shopkeeper.shop_name or "Shop"
        rows = shopkeeper.list_inventory()

        if not rows:
            caller.msg(f"|w=== {shop_name} ===|n\nThe shelves are empty.")
            return

        lines = [f"|w=== {shop_name} ===|n"]
        for row in rows:
            lines.append(f"  {row['name']}")

        lines.append("")
        lines.append(shopkeeper.quote_hint())
        caller.msg("\n".join(lines))


# ── CmdShopAccept ────────────────────────────────────────────────────


class CmdShopAccept(FCMCommandMixin, Command):
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

        # Clear the quote slot BEFORE executing so a mid-flight failure
        # can't be retried against a dead quote.
        caller.ndb.pending_quote = None

        if quote["direction"] == "buy":
            shopkeeper.execute_buy(caller, quote)
        else:
            shopkeeper.execute_sell(caller, quote)


# ── Base cmdset ──────────────────────────────────────────────────────


class ShopCmdSet(CmdSet):
    """Base cmdset for shopkeepers — list + accept only.

    Concrete shop cmdsets inherit from this and add the buy/sell/quote
    commands whose grammar differs between resource and NFT shops.
    """

    key = "ShopCmdSet"
    priority = 1
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdShopList())
        self.add(CmdShopAccept())

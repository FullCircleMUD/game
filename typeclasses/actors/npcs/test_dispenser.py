"""
Test dispensers — vending machines that hand out stock for free, so a
tester can get at any item or resource without grinding for it.

**Test-only. Never place one in a live zone.**

Why these are separate typeclasses rather than a ``free = True`` flag on
the ordinary shopkeepers: a flag lives on the production class, so a
single wrong line in a millholm YAML file would turn a real shop into an
open tap into the game economy. A separate typeclass has no such line to
get wrong — a live shop would have to name the test class outright.

Containment is four independent layers:

1. These classes are referenced only from test-world YAML.
2. That YAML exists only on the fcm-world ``test`` branch.
3. CI on ``main`` rejects any YAML referencing this module.
4. `wb_build` only builds what the configured `WORLDBUILDER_REF` points at,
   and production points at ``main``.

**Do not rename or move this module.** The CI guard
(``.github/workflows/no-test-world-on-main.yml`` in fcm-world) matches on
the dotted path ``typeclasses.actors.npcs.test_dispenser`` rather than on
the class names, so that it keeps working as dispensers are added. Renaming
the module silently disables layer 3.

Both classes are thin: they inherit the whole ``list`` / ``quote`` / ``buy``
command surface and the fulfilment machinery from their shopkeeper parents,
and override only pricing, listing and settlement.

Free dispensing runs synchronously on the reactor rather than in a worker
thread, unlike the parents' buy paths. That is deliberate and safe: the
parents thread because the AMM swap makes a real XRPL call, whereas
``assign_to_blank_token`` and ``receive_resource_from_reserve`` resolve to
plain Django transactions against the mirror database. There is no network
round trip to keep off the reactor, and settlement still goes through the
encapsulation layer, so the mirror cannot desync.

Descriptions live in YAML, not here — see the vending machine files under
``shard0/test-world/`` in fcm-world. This module only owns behaviour and
the flavour text of a dispense.
"""

from typeclasses.actors.npcs.nft_shopkeeper import NFTShopkeeperNPC
from typeclasses.actors.npcs.resource_shopkeeper import ResourceShopkeeperNPC


def _article(name):
    """"a" or "an" to suit the item name.

    Item names come straight from the catalogue, so the dispense message
    has to cope with both "a Bronze Dagger" and "an Adamantine Dagger".
    A vowel check is enough for this catalogue — there are no "a hour"
    or "an unicorn" cases in it.
    """
    return "an" if name[:1].lower() in "aeiou" else "a"


class TestNFTDispenser(NFTShopkeeperNPC):
    """Vends any NFT item type for free. Test-only.

    Beyond being free, this lifts the parent's ``tracking_token`` filter.
    That filter is correct for a real shop — an item type with no proxy
    AMM pool cannot be priced — but it hides roughly three quarters of the
    catalogue, including every recipe and every spell scroll. Since a
    dispenser never prices anything, it can stock the whole catalogue.

    ``inventory`` holds NFTItemType.name strings, same as the parent.
    """

    # ── Listing: no tracking_token filter ───────────────────────────

    def list_inventory(self):
        """Every stocked item type, priceable or not."""
        from blockchain.xrpl.models import NFTItemType
        return [
            {"name": item_type.name, "item_key": item_type.name}
            for item_type in NFTItemType.objects.filter(
                name__in=list(self.inventory or []),
            )
        ]

    def get_tradeable_types(self):
        """Command-side counterpart of list_inventory — also unfiltered."""
        from blockchain.xrpl.models import NFTItemType
        return NFTItemType.objects.filter(name__in=list(self.inventory or []))

    # ── Pricing: always free ────────────────────────────────────────

    def get_buy_price(self, item_key, qty=1):
        return 0

    def get_sell_price(self, item_key, qty=1):
        return 0

    def quote_hint(self):
        return "Everything here is |gfree|n — just |wbuy <item>|n."

    # ── Settlement: dispense, no gold ───────────────────────────────

    def execute_buy(self, caller, quote):
        """Assign a blank token and spawn the item straight into inventory."""
        assert quote.get("qty", 1) == 1, "NFT dispensers vend singletons only"
        item_type_name = quote["item_key"]

        from blockchain.xrpl.models import NFTItemType
        from typeclasses.items.base_nft_item import BaseNFTItem

        try:
            token_id = BaseNFTItem.assign_to_blank_token(item_type_name)
        except NFTItemType.DoesNotExist:
            # Almost always a typo in the machine's YAML stock list.
            caller.msg(
                f"|rThe display flashes:|n |yUNKNOWN PRODUCT CODE — "
                f"'{item_type_name}'|n"
            )
            return
        except ValueError as err:
            # The blank-token reserve pool is finite. Despawning dispensed
            # items returns their tokens to the pool.
            caller.msg(
                f"|rThe machine buzzes angrily.|n |ySOLD OUT.|n ({err})"
            )
            return

        item = BaseNFTItem.spawn_into(token_id, caller)
        if item is None:
            caller.msg(
                f"|rThe machine whirrs, clunks, and delivers nothing.|n "
                f"Token {token_id} has no mirror row to spawn from."
            )
            return

        caller.msg(
            f"|cThe machine hums, and a {item_type_name} thumps into the "
            f"tray.|n You take it. |g(free)|n"
        )
        caller.location.msg_contents(
            "$You() $conj(take) something from the vending machine's tray.",
            from_obj=caller,
            exclude=[caller],
        )

    def execute_sell(self, caller, quote):
        """Dispensers vend only — nothing to sell into, and no gold to pay."""
        caller.msg("|yThe machine has no coin slot. It only gives.|n")


class TestResourceDispenser(ResourceShopkeeperNPC):
    """Vends any quantity of any resource for free. Test-only.

    The parent needs no listing override — it already lists whatever
    resource IDs it is given, without a tradeability filter, because every
    resource has an AMM pool. Only pricing and settlement change here.

    ``inventory`` holds int resource IDs, same as the parent.
    """

    # ── Pricing: always free ────────────────────────────────────────

    def get_buy_price(self, item_key, qty=1):
        return 0

    def get_sell_price(self, item_key, qty=1):
        return 0

    def quote_hint(self):
        return "Everything here is |gfree|n — just |wbuy <amount> <item>|n."

    # ── Settlement: dispense, no gold ───────────────────────────────

    def execute_buy(self, caller, quote):
        """Move the resource from reserve to the caller, charging nothing."""
        resource_id = quote["item_key"]
        qty = quote["qty"]
        display = quote.get("display") or self._display_for(resource_id, qty)

        caller.receive_resource_from_reserve(resource_id, qty)

        caller.msg(
            f"|cThe machine rumbles and dispenses {display}.|n |g(free)|n"
        )
        caller.location.msg_contents(
            "$You() $conj(collect) something from the vending machine's tray.",
            from_obj=caller,
            exclude=[caller],
        )

    def execute_sell(self, caller, quote):
        """Dispensers vend only — nothing to sell into, and no gold to pay."""
        caller.msg("|yThe machine has no coin slot. It only gives.|n")

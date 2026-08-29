"""
Stew command — buy and eat a bowl of stew at the inn.

Purchases 1 bread via the AMM pool at the current market price, then
immediately consumes it to raise the character's hunger level. The player
never sees the bread — they just buy stew and get fed.

This connects inn food consumption to the broader resource economy:
every bowl of stew moves the bread AMM price.

Fallback: if no AMM pool exists (no liquidity), uses a static price
and sinks the gold directly.

Usage:
    stew
"""

from django.conf import settings
from django.db import transaction
from utils.db_threads import defer_to_db_thread

from evennia import Command

from commands.command import FCMCommandMixin
from commands.room_specific_cmds.inn.service import bartender_refuses
from enums.hunger_level import HungerLevel
from utils.attribute_cache import discard_cached_attributes


BREAD_RESOURCE_ID = 3
FALLBACK_PRICE = 5  # static gold price when no AMM pool exists


class CmdStew(FCMCommandMixin, Command):
    """
    Buy and eat a bowl of stew.

    Usage:
        stew

    Costs gold at the current market price of bread.
    Increases your hunger level by one.
    """

    key = "stew"
    locks = "cmd:all()"
    help_category = "Inn"

    def func(self):
        caller = self.caller

        if bartender_refuses(caller):
            return

        current = caller.hunger_level
        if current == HungerLevel.FULL:
            caller.msg("You are already full.")
            return

        # Try AMM-priced purchase
        wallet = caller._get_wallet()
        if not wallet or wallet == settings.XRPL_VAULT_ADDRESS:
            # Superuser / no wallet — use fallback static price
            self._buy_static(caller, current)
            return

        char_key = caller._get_character_key()
        vault = settings.XRPL_VAULT_ADDRESS
        current_gold = caller.get_gold()

        caller.msg("|cThe bartender ladles a bowl of stew...|n")
        d = defer_to_db_thread(
            _threaded_stew_buy, current_gold, wallet, char_key, vault,
        )
        d.addCallback(
            lambda data: _on_stew_complete(caller, current, data[0], data[1])
        )
        d.addErrback(
            lambda f: _on_stew_error(caller, f)
        )

    def _buy_static(self, caller, current):
        """Fallback: static price when no AMM pool exists."""
        if not caller.has_gold(FALLBACK_PRICE):
            caller.msg(
                f"You can't afford that. Stew costs {FALLBACK_PRICE} gold."
            )
            return

        caller.return_gold_to_sink(FALLBACK_PRICE)
        _apply_hunger(caller, current, FALLBACK_PRICE)


def _threaded_stew_buy(current_gold, wallet, char_key, vault):
    """
    Worker thread — get the bread price, then execute the on-chain swap.

    The swap only. Booking it happens on the reactor thread, in a
    transaction alongside the player's local writes — see _book_stew_buy().
    """
    from blockchain.xrpl.services.amm import AMMService

    try:
        gold_cost = AMMService.get_buy_price(BREAD_RESOURCE_ID, 1)
    except Exception:
        # No AMM pool — use fallback
        return (None, None)

    if current_gold < gold_cost:
        raise ValueError(
            f"Stew costs {gold_cost} gold today, but you only have "
            f"{current_gold}."
        )

    swap_result = AMMService.buy_resource_swap(
        BREAD_RESOURCE_ID, 1, gold_cost,
    )
    return (gold_cost, swap_result)


def _book_stew_buy(caller, gold_cost, swap_result):
    """
    Hold the player's local writes and the ownership write together.

    The swap ran in the worker thread and is outside this transaction — one
    cannot be held open across a ledger round-trip. Inside is the pair that
    has to agree: what the game says the player holds and what the xrpl
    database says they own. Local writes go first, so a failure in the
    ownership write takes them with it.
    """
    from blockchain.xrpl.services.amm import AMMService

    wallet = caller._get_wallet()
    char_key = caller._get_character_key()
    vault = settings.XRPL_VAULT_ADDRESS

    try:
        with transaction.atomic():
            caller._remove_gold(gold_cost)
            caller._add_resource(BREAD_RESOURCE_ID, 1)
            AMMService.buy_resource_record(
                wallet, char_key, BREAD_RESOURCE_ID, 1, gold_cost, vault,
                swap_result,
            )
    except Exception:
        # The rows are back; the in-memory Attributes are not.
        discard_cached_attributes(caller)
        raise


def _on_stew_complete(caller, hunger_before, gold_cost, swap_result):
    """
    Reactor thread — book the purchase, consume the bread, feed the player.

    The swap has already happened and cannot be undone, so this runs whether
    or not the player is still connected; a disconnect mid-purchase feeds
    them rather than wasting the bowl. Only the messages need a session.
    """
    if gold_cost is None:
        # AMM fallback — use static price
        if not caller.has_gold(FALLBACK_PRICE):
            caller.msg(
                f"You can't afford that. Stew costs {FALLBACK_PRICE} gold."
            )
            return
        caller.return_gold_to_sink(FALLBACK_PRICE)
        _apply_hunger(caller, hunger_before, FALLBACK_PRICE)
        return

    _book_stew_buy(caller, gold_cost, swap_result)

    # Consuming it is a separate operation, deliberately. It opens its own
    # transaction, and putting it inside the one above would leave a write
    # to the default database after the ownership write had committed. If
    # this fails the player keeps the bread they paid for — not the outcome
    # they asked for, but nothing is lost.
    caller.return_resource_to_sink(BREAD_RESOURCE_ID, 1)

    _apply_hunger(caller, hunger_before, gold_cost)


def _on_stew_error(caller, failure):
    """Reactor thread — handle purchase failure."""
    if not caller.sessions.count():
        return

    error = failure.value
    caller.msg(f"|rThe bartender shakes his head — {error}|n")


def _apply_hunger(caller, current, gold_cost):
    """
    Apply the hunger effect and describe it.

    No session check. A player who dropped out mid-purchase has still eaten,
    and msg() to a character with no sessions goes nowhere by itself — while
    the room message should still reach whoever is watching.
    """
    new_level = HungerLevel(current.value + 1)
    caller.hunger_level = new_level

    if new_level == HungerLevel.FULL:
        caller.hunger_free_pass_tick = True

    caller.msg(
        f"You eat a warm bowl of stew. ({gold_cost} gold)"
    )
    caller.msg(new_level.get_hunger_message())
    caller.location.msg_contents(
        f"{caller.key} tucks into a warm bowl of stew.",
        exclude=[caller],
        from_obj=caller,
    )

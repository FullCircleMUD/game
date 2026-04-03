"""
Stew command — buy and eat a bowl of stew at the inn.

Purchases 1 bread via the AMM pool at the current market price, then
immediately consumes it to raise the character's hunger level. The player
never sees the bread — they just buy stew and get fed.

This connects inn food consumption to the broader resource economy:
every bowl of stew moves the bread AMM price.

Fallback: if no AMM pool exists (testnet, no liquidity), uses a static
price and sinks the gold directly.

Usage:
    stew
"""

from django.conf import settings
from twisted.internet import threads

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from enums.hunger_level import HungerLevel


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

        if hasattr(caller, "has_condition") and (
            caller.has_condition(Condition.HIDDEN)
            or caller.has_condition(Condition.INVISIBLE)
        ):
            caller.msg(
                "The bartender looks around wildly, trying to identify "
                "where the voice is coming from. No service."
            )
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
        d = threads.deferToThread(
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
    """Worker thread — get bread price then execute AMM swap."""
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

    result = AMMService.buy_resource(
        wallet, char_key, BREAD_RESOURCE_ID, 1, gold_cost, vault,
    )
    return (gold_cost, result)


def _on_stew_complete(caller, hunger_before, gold_cost, result):
    """Reactor thread — update Evennia state and feed the character."""
    if not caller.sessions.count():
        return

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

    # AMM purchase succeeded — update local Evennia attributes
    caller._remove_gold(gold_cost)
    caller._add_resource(BREAD_RESOURCE_ID, 1)

    # Immediately consume the bread
    caller.return_resource_to_sink(BREAD_RESOURCE_ID, 1)

    _apply_hunger(caller, hunger_before, gold_cost)


def _on_stew_error(caller, failure):
    """Reactor thread — handle purchase failure."""
    if not caller.sessions.count():
        return

    error = failure.value
    caller.msg(f"|rThe bartender shakes his head — {error}|n")


def _apply_hunger(caller, current, gold_cost):
    """Apply the hunger effect and send messages."""
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

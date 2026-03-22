"""
Stew command — buy and eat a bowl of stew at the inn.

Costs gold (consumed into sink) and increments hunger level.

Usage:
    stew
"""

from evennia import Command

from enums.condition import Condition
from enums.hunger_level import HungerLevel

# Price in gold — static for now, will draw from market makers later.
STEW_PRICE = 1


class CmdStew(Command):
    """
    Buy and eat a bowl of stew.

    Usage:
        stew

    Costs {price} gold. Increases your hunger level by one.
    """.format(price=STEW_PRICE)

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

        if not caller.has_gold(STEW_PRICE):
            caller.msg(f"You can't afford that. Stew costs {STEW_PRICE} gold.")
            return

        current = caller.hunger_level
        if current == HungerLevel.FULL:
            caller.msg("You are already full.")
            return

        caller.return_gold_to_sink(STEW_PRICE)

        new_level = HungerLevel(current.value + 1)
        caller.hunger_level = new_level

        if new_level == HungerLevel.FULL:
            caller.hunger_free_pass_tick = True

        caller.msg("You eat a warm bowl of stew.")
        caller.msg(new_level.get_hunger_message())
        caller.location.msg_contents(
            f"{caller.key} tucks into a warm bowl of stew.",
            exclude=[caller],
            from_obj=caller,
        )

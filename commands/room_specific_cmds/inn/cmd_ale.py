"""
Ale command — buy and drink a mug of ale at the inn.

Costs gold (consumed into sink). No hunger effect.

Usage:
    ale
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition

# Price in gold — static for now, will draw from market makers later.
ALE_PRICE = 1


class CmdAle(FCMCommandMixin, Command):
    """
    Buy and drink a mug of ale.

    Usage:
        ale

    Costs {price} gold.
    """.format(price=ALE_PRICE)

    key = "ale"
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

        if not caller.has_gold(ALE_PRICE):
            caller.msg(f"You can't afford that. Ale costs {ALE_PRICE} gold.")
            return

        caller.return_gold_to_sink(ALE_PRICE)

        caller.msg("You drink a frothy mug of ale. A warm feeling spreads through you.")
        caller.location.msg_contents(
            f"{caller.key} raises a mug of ale and drinks heartily.",
            exclude=[caller],
            from_obj=caller,
        )

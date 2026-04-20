"""
Ale command — buy and drink a mug of ale at the inn.

Costs gold (consumed into sink). Restores ONE stage of thirst per mug
(parallel to how stew raises hunger by one level per bowl). No hunger
effect — order food for that.

Usage:
    ale
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition
from enums.thirst_level import ThirstLevel

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

        if hasattr(caller, "thirst_level") and caller.thirst_level == ThirstLevel.REFRESHED:
            caller.msg("You are not thirsty.")
            return

        if not caller.has_gold(ALE_PRICE):
            caller.msg(f"You can't afford that. Ale costs {ALE_PRICE} gold.")
            return

        caller.return_gold_to_sink(ALE_PRICE)

        # Step thirst up one stage — parallel to how stew steps hunger up
        # one level per bowl. Drink multiple ales to fully refresh.
        if hasattr(caller, "thirst_level") and isinstance(caller.thirst_level, ThirstLevel):
            current = caller.thirst_level
            if current != ThirstLevel.REFRESHED:
                new_level = ThirstLevel(current.value + 1)
                caller.thirst_level = new_level
                # Free-pass tick only when the drink lands them at REFRESHED,
                # mirroring the stew → FULL behaviour.
                if new_level == ThirstLevel.REFRESHED:
                    caller.thirst_free_pass_tick = True

        caller.msg("You drink a frothy mug of ale. A warm feeling spreads through you.")
        caller.location.msg_contents(
            f"{caller.key} raises a mug of ale and drinks heartily.",
            exclude=[caller],
            from_obj=caller,
        )

"""
Drink command — sip from a water container in your inventory.

Usage:
    drink                — drink from the first non-empty water container
                            in your inventory
    drink <container>    — drink from a specific container by name

Each drink restores one thirst stage. Containers (canteens, casks) are
inventory items, NOT held — you can drink while wielding a weapon and
holding a torch, the same way you can eat bread mid-combat.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


class CmdDrink(FCMCommandMixin, Command):
    """
    Drink water from a canteen, cask, or other water container in your
    inventory. Restores one thirst stage per drink.

    Usage:
        drink
        drink <container>
    """

    key = "drink"
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller
        query = self.args.strip()

        # Darkness — can't identify items without sight
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        if query:
            container, _ = resolve_target(
                caller, query, "items_inventory",
                extra_predicates=(p_can_see,),
            )
            if not container:
                caller.msg(f"You aren't carrying '{query}'.")
                return
            if not getattr(container, "is_water_container", False):
                caller.msg(f"You can't drink from {container.key}.")
                return
        else:
            container = self._first_non_empty_container(caller)
            if container is None:
                caller.msg("You have nothing to drink from.")
                return

        success, msg = container.drink_from(caller)
        if not success:
            caller.msg(msg)
            return

        caller.msg(f"|cYou drink from {container.key}.|n")
        if caller.location:
            caller.location.msg_contents(
                f"$You() $conj(drink) from {container.key}.",
                from_obj=caller,
                exclude=[caller],
            )

    @staticmethod
    def _first_non_empty_container(caller):
        for obj in caller.contents:
            if not getattr(obj, "is_water_container", False):
                continue
            if getattr(obj, "is_empty", True):
                continue
            return obj
        return None

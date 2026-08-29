"""
Refuel command — refuel a lantern or other reusable light source.

Usage:
    refuel <item>
    refill <item>

Consumes 1 oil from the player's fungible inventory and resets the
light source's fuel to maximum. Fails if the lantern is already full
or the player has no oil. Oil is processed from Animal Fat at a tannery.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.busy import (
    FUMBLE_BUSY_MESSAGE,
    FUMBLE_MOVE_MESSAGE,
    check_busy,
    fumble_seconds,
    start_busy,
)
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_perceive
from utils.visibility import looker_is_blind


FUEL_RESOURCE_ID = 46  # Oil (processed from Animal Fat at tannery)
FUEL_RESOURCE_NAME = "oil"
FUEL_COST = 1  # units consumed per refuel


class CmdRefuel(FCMCommandMixin, Command):
    """
    Refuel a lantern or light source.

    Usage:
        refuel <item>
        refill <item>

    Consumes 1 oil to refuel a lantern to full capacity.
    """

    key = "refuel"
    aliases = []
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Refuel what?")
            return

        query = self.args.strip()

        if check_busy(caller):
            return

        # No sight check — the lantern is in your own pack or on your
        # own belt, and pouring by feel is slow rather than impossible.
        # The search runs before the outcome is known.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._refuel(caller, query),
                self_msg="You fumble blindly through your pack, then pour by touch...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._refuel(caller, query)

    def _refuel(self, caller, query):
        """Find the light source and fill it. Success or failure both."""
        # Search inventory first, then equipped (held lantern)
        item, _ = resolve_target(
            caller, query, "items_inventory",
            extra_predicates=(p_can_perceive,),
        )
        item = item[0] if item else None
        if not item:
            item, _ = resolve_target(
                caller, query, "items_equipped",
                extra_predicates=(p_can_perceive,),
            )
            item = item[0] if item else None
        if not item:
            caller.msg(f"You aren't carrying '{query}'.")
            return

        # Must be a light source
        if not getattr(item, "is_light_source", False):
            caller.msg("That's not something you can refuel.")
            return

        # Can't refuel infinite fuel sources
        if item.max_fuel < 0:
            caller.msg(f"{item.key} doesn't need fuel.")
            return

        # Can't refuel consumable lights (torches) — they're single-use
        if getattr(item, "is_consumable_light", False):
            caller.msg(f"You can't refuel {item.key}. It's single-use.")
            return

        # Already full?
        if item.fuel_remaining >= item.max_fuel:
            caller.msg(f"{item.key} is already full.")
            return

        # Check fuel resource
        available = caller.get_resource(FUEL_RESOURCE_ID)
        if available < FUEL_COST:
            caller.msg(
                f"You need {FUEL_COST} {FUEL_RESOURCE_NAME} to refuel "
                f"{item.key} but you don't have any."
            )
            return

        # Consume fuel and refill
        caller.return_resource_to_sink(FUEL_RESOURCE_ID, FUEL_COST)
        item.fuel_remaining = item.max_fuel

        caller.msg(
            f"|gYou pour {FUEL_RESOURCE_NAME} into {item.key}, "
            f"refueling it to full.|n"
        )
        caller.location.msg_contents(
            f"$You() $conj(refuel) {item.key}.",
            from_obj=caller,
            exclude=[caller],
        )

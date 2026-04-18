"""
Refuel command — refuel a lantern or other reusable light source.

Usage:
    refuel <item>
    refill <item>

Consumes 1 wheat (oil substitute) from the player's fungible inventory
and resets the light source's fuel to maximum. Fails if the lantern is
already full or the player has no wheat.

When oil is added as a resource, swap FUEL_RESOURCE_ID to the oil ID.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


# Resource ID for fuel. Currently wheat (ID 1) as an oil placeholder.
# Swap to oil resource ID when it exists.
FUEL_RESOURCE_ID = 1
FUEL_RESOURCE_NAME = "wheat"
FUEL_COST = 1  # units consumed per refuel


class CmdRefuel(FCMCommandMixin, Command):
    """
    Refuel a lantern or light source.

    Usage:
        refuel <item>
        refill <item>

    Consumes 1 wheat to refuel a lantern to full capacity.
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

        # Darkness — need sight to pour fuel
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        # Search inventory first, then equipped (held lantern)
        item, _ = resolve_target(
            caller, query, "items_inventory",
            extra_predicates=(p_can_see,),
        )
        if not item:
            item, _ = resolve_target(
                caller, query, "items_equipped",
                extra_predicates=(p_can_see,),
            )
        if not item:
            caller.msg(f"You aren't carrying '{query}'.")
            return
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

"""
CmdExplore — attempt to discover hidden destinations at a gateway.

Each bread the player carries = one day of exploration = one roll against
the destination's explore_chance. Success discovers the destination
permanently and teleports the player there.
"""

import random

from evennia import Command

from commands.room_specific_cmds.gateway.cmd_travel import (
    BREAD_RESOURCE_ID,
    validate_conditions,
    is_destination_visible,
)


class CmdExplore(Command):
    """
    Explore to discover unknown destinations from this gateway.

    Each bread you carry gives one day of exploration. More bread means
    more chances to find something before you must turn back.

    Usage:
        explore
    """

    key = "explore"
    locks = "cmd:all()"
    help_category = "Travel"

    def func(self):
        caller = self.caller
        room = caller.location

        destinations = room.destinations if hasattr(room, "destinations") else []

        # Collect hidden destinations the caller hasn't discovered
        # and meets non-food conditions for
        explorable = []
        for dest in destinations:
            if not dest.get("hidden", False):
                continue
            # Already visible (discovered or has chart) → skip
            if is_destination_visible(caller, dest, room):
                continue
            # Check non-food, non-gold conditions
            conditions = dict(dest.get("conditions", {}))
            conditions.pop("food_cost", None)
            conditions.pop("gold_cost", None)
            ok, _ = validate_conditions(caller, conditions)
            if ok:
                explorable.append(dest)

        if not explorable:
            caller.msg("There's nothing new to discover from here.")
            return

        # Check bread supply
        bread_available = caller.get_resource(BREAD_RESOURCE_ID)
        if bread_available <= 0:
            caller.msg("You need food for the journey. Bring bread.")
            return

        # Pay gold cost up front (from a random explorable dest)
        target = random.choice(explorable)
        gold_cost = target.get("conditions", {}).get("gold_cost", 0)
        if gold_cost:
            if not caller.has_gold(gold_cost):
                caller.msg(
                    f"Exploration costs {gold_cost} gold to outfit. "
                    f"You have {caller.get_gold()}."
                )
                return
            caller.return_gold_to_sink(gold_cost)

        # Roll loop — each bread = one day
        explore_chance = target.get("explore_chance", 20)
        days = 0

        caller.msg("\n|c--- Setting Out to Explore ---|n")

        for day in range(1, bread_available + 1):
            caller._remove_resource(BREAD_RESOURCE_ID, 1)
            days = day

            roll = random.randint(1, 100)
            if roll <= explore_chance:
                # Success!
                self._discover(caller, room, target, days)
                return

        # All rolls failed
        caller.msg(
            f"\nAfter {days} days you find nothing and limp back "
            f"with empty stores."
        )

    def _discover(self, caller, room, dest, days):
        """Handle successful discovery — spawn a route map NFT."""
        dest_key = dest.get("key", "")
        gateway_key = room.key
        label = dest.get("label", "an unknown place")

        # Spawn route map NFT
        from typeclasses.items.base_nft_item import BaseNFTItem
        try:
            token_id, _, _ = BaseNFTItem.assign_to_blank_token("RouteMap")
            obj = BaseNFTItem.spawn_into(token_id, caller)
            if obj:
                obj.route_key = f"{gateway_key}:{dest_key}"
                obj.departure_name = room.key
                obj.destination_name = label
                # Update key for searchability
                obj.key = f"route map to {label}".lower()
                caller.msg(
                    f"|gA route map to {label} materialises in your pack.|n"
                )
        except Exception as exc:
            # Fallback — don't block discovery if NFT spawn fails
            caller.msg(
                f"|y[Warning] Route map could not be created: {exc}. "
                f"You discovered the route but received no map.|n"
            )

        # Narrative
        travel_desc = dest.get(
            "travel_description",
            f"After {days} days of exploration, you discover {label}!",
        )
        caller.msg(f"\n|yAfter {days} days of exploration, you discover {label}!|n")
        caller.msg(travel_desc)

        destination_room = dest.get("destination")
        if not destination_room:
            caller.msg("But the way forward is blocked... (destination not connected)")
            return

        # Departure message
        room.msg_contents(
            f"{caller.key} sets off exploring and disappears from view.",
            exclude=[caller],
        )

        # Teleport
        caller.move_to(destination_room, quiet=True, move_type="teleport")

        # Arrival message
        destination_room.msg_contents(
            f"{caller.key} arrives, looking weathered from their journey.",
            exclude=[caller],
        )

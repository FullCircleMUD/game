"""
CmdSail — sail a ship to a known destination via a dock room.

Usage:
    sail                       — list sea routes from this dock
    sail <destination>         — show qualifying ships (auto-sails if only one)
    sail <destination> <#>     — sail with the chosen ship

Requires SEAMANSHIP skill (general, all classes). The dock room must be a
RoomGateway with destinations that have a ``boat_level`` condition set.
The player must own a ShipNFTItem in their contents with a sufficient
ship_tier (1–5 matching BASIC–GRANDMASTER).
"""

from enums.mastery_level import MasteryLevel
from enums.ship_type import ShipType
from enums.skills_enum import skills
from commands.room_specific_cmds.gateway.cmd_travel import (
    validate_conditions,
    consume_costs,
    is_destination_visible,
    _delayed_travel,
    _SEA_MESSAGES,
)
from .cmd_skill_base import CmdSkillBase


def _get_qualifying_ships(character, min_tier):
    """Return ShipNFTItem objects from character.contents with ship_tier >= min_tier."""
    from typeclasses.items.untakeables.ship_nft_item import ShipNFTItem
    return [
        obj for obj in character.contents
        if isinstance(obj, ShipNFTItem) and obj.ship_tier >= min_tier
    ]


class CmdSail(CmdSkillBase):
    """
    Sail a ship to a known destination.

    Usage:
        sail                       — list sea routes from this dock
        sail <destination>         — choose a ship or auto-sail
        sail <destination> <#>     — sail with the chosen ship
    """

    key = "sail"
    skill = skills.SEAMANSHIP.value
    help_category = "Exploration"

    def unskilled_func(self):
        self.caller.msg("You have no knowledge of seamanship.")

    def basic_func(self):
        self._do_sail()

    def skilled_func(self):
        self._do_sail()

    def expert_func(self):
        self._do_sail()

    def master_func(self):
        self._do_sail()

    def grandmaster_func(self):
        self._do_sail()

    # ── Shared logic ────────────────────────────────────────────────

    def _do_sail(self):
        caller = self.caller
        room = caller.location

        if caller.ndb.is_processing:
            caller.msg("You are already busy. Wait until your current task finishes.")
            return

        destinations = getattr(room, "destinations", None)
        if not destinations:
            caller.msg("There are no sea routes from here.")
            return

        # Only show destinations that require a ship (boat_level set)
        sail_dests = [
            d for d in destinations
            if d.get("conditions", {}).get("boat_level")
            and is_destination_visible(caller, d, room)
        ]

        if not sail_dests:
            caller.msg("There are no sea routes from here.")
            return

        # Parse args: <destination> [ship_number]
        raw = self.args.strip()
        if not raw:
            # No args — list destinations (or auto-pick if single)
            if len(sail_dests) == 1:
                self._prepare_voyage(caller, room, sail_dests[0])
            else:
                self._list_destinations(caller, sail_dests)
            return

        dest_search, ship_choice = self._parse_args(raw)

        # Match destination
        match = None
        for d in sail_dests:
            if (d.get("key", "").lower() == dest_search.lower()
                    or d.get("label", "").lower().startswith(
                        dest_search.lower())):
                match = d
                break
        if not match:
            caller.msg(f"No known destination matching '{dest_search}'.")
            return

        self._prepare_voyage(caller, room, match, ship_choice)

    def _parse_args(self, raw):
        """
        Split args into (dest_search, ship_choice).

        If the last token is a bare integer, treat it as ship choice.
        """
        parts = raw.rsplit(None, 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0], int(parts[1])
        return raw, None

    def _prepare_voyage(self, caller, room, dest, ship_choice=None):
        """Validate conditions, select ship, and execute voyage."""
        conditions = dest.get("conditions", {})
        required_tier = conditions.get("boat_level", 0)

        # Validate non-boat conditions first (food, gold, level)
        non_boat = {k: v for k, v in conditions.items() if k != "boat_level"}
        ok, msg = validate_conditions(caller, non_boat)
        if not ok:
            caller.msg(msg)
            return

        destination_room = dest.get("destination")
        if not destination_room:
            caller.msg("This route's destination is not connected.")
            return

        # Get qualifying ships from character contents
        qualifying = _get_qualifying_ships(caller, required_tier)
        if not qualifying:
            needed = MasteryLevel(required_tier).name
            caller.msg(
                f"You need at least a {needed}-tier ship for this voyage. "
                f"You don't own any qualifying ships."
            )
            return

        # Single ship — auto-select
        if len(qualifying) == 1:
            ship = qualifying[0]
            caller.msg(f"You board your {ship.key}.")
            self._execute_voyage(caller, room, dest, ship)
            return

        # Multiple ships — need a choice
        if ship_choice is None:
            self._list_ships(caller, qualifying, dest)
            return

        # Validate choice
        if ship_choice < 1 or ship_choice > len(qualifying):
            caller.msg(
                f"Invalid choice. Enter a number between 1 and {len(qualifying)}."
            )
            return

        ship = qualifying[ship_choice - 1]
        caller.msg(f"You board your {ship.key}.")
        self._execute_voyage(caller, room, dest, ship)

    def _execute_voyage(self, caller, room, dest, ship):
        """Consume costs, show travel delay, teleport, update ship location."""
        conditions = dest.get("conditions", {})
        consume_costs(caller, conditions)

        travel_desc = dest.get(
            "travel_description", "You cast off and sail into open waters..."
        )
        caller.msg(f"\n{travel_desc}")

        destination_room = dest["destination"]

        def _arrive():
            caller.move_to(destination_room, quiet=True, move_type="teleport")
            destination_room.msg_contents(
                f"{caller.key} arrives by ship.",
                exclude=[caller],
            )
            ship.arrive_at_dock(destination_room)

        _delayed_travel(caller, room, dest, _SEA_MESSAGES, _arrive)

    def _list_destinations(self, caller, sail_dests):
        """List available sea routes."""
        caller.msg("\n|c--- Sea Routes ---|n")
        for d in sail_dests:
            label = d.get("label", d.get("key", "???"))
            conditions = d.get("conditions", {})
            reqs = self._format_requirements(conditions)
            caller.msg(f"  |w{label}|n ({d.get('key', '')}){reqs}")
        caller.msg("\nUse |wsail <destination>|n to set sail.")

    def _list_ships(self, caller, qualifying, dest):
        """Show qualifying ships for the player to choose from."""
        dest_key = dest.get("key", "")
        caller.msg("\n|c--- Choose Your Ship ---|n")
        for i, ship in enumerate(qualifying, 1):
            try:
                tier_name = ShipType(ship.ship_tier).item_type_name
            except (ValueError, KeyError):
                tier_name = "Unknown"
            caller.msg(f"  {i}. {ship.key} ({tier_name})")
        caller.msg(
            f"\nUse |wsail {dest_key} <number>|n to set sail."
        )

    def _format_requirements(self, conditions):
        """Format requirement summary for listing."""
        parts = []
        if conditions.get("boat_level"):
            tier_name = MasteryLevel(conditions["boat_level"]).name
            parts.append(f"{tier_name}-tier ship")
        if conditions.get("food_cost"):
            parts.append(f"{conditions['food_cost']} bread")
        if conditions.get("gold_cost"):
            parts.append(f"{conditions['gold_cost']} gold")
        if conditions.get("level_required"):
            parts.append(f"Level {conditions['level_required']}")
        if not parts:
            return ""
        return " — " + ", ".join(parts)

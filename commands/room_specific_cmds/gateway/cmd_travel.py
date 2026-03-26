"""
CmdTravel — travel between zones via gateway rooms.

Usage:
    travel                  — list destinations or travel if only one
    travel <destination>    — travel to a named destination
"""

from evennia import Command
from evennia.utils import delay


BREAD_RESOURCE_ID = 3

# ── Travel delay configuration ─────────────────────────────────────────
TRAVEL_TICK_SECONDS = 2

_TRAVEL_MESSAGES = [
    "The road stretches ahead, winding through unfamiliar lands...",
    "You grow weary from days of travel, but press on...",
]

_SEA_MESSAGES = [
    "The sails catch the wind and the harbour shrinks behind you...",
    "Days pass on open water. The horizon is endless...",
]

_EXPLORE_MESSAGES = [
    "You push into uncharted territory, marking your trail...",
    "The landscape shifts as you venture further from known paths...",
]


def _delayed_travel(caller, room, dest, messages, on_arrive):
    """
    Show staggered travel messages then call on_arrive().

    Uses the same ndb.is_processing / delay() pattern as crafting.
    """
    caller.ndb.is_processing = True
    label = dest.get("label", "parts unknown")
    room.msg_contents(
        f"{caller.key} sets off on their journey to {label}.",
        exclude=[caller],
    )

    def _tick(step):
        if step < len(messages):
            caller.msg(messages[step])
            delay(TRAVEL_TICK_SECONDS, _tick, step + 1)
        else:
            caller.ndb.is_processing = False
            on_arrive()

    delay(TRAVEL_TICK_SECONDS, _tick, 0)


# ── Condition validators ─────────────────────────────────────────────
# Each returns (ok, failure_message). Checked in order; first failure shown.

def _check_level(caller, conditions):
    req = conditions.get("level_required")
    if req and caller.total_level < req:
        return False, f"You must be at least level {req} to make this journey. You are level {caller.total_level}."
    return True, ""


def _check_mounted(caller, conditions):
    if conditions.get("mounted"):
        return False, "You need a mount for this journey. (Mounts not yet implemented.)"
    return True, ""


def _check_fly(caller, conditions):
    if conditions.get("fly"):
        return False, "This destination is only reachable by air. (Flying mounts not yet implemented.)"
    return True, ""


def _check_water_breathing(caller, conditions):
    if conditions.get("water_breathing"):
        return False, "You need water breathing for this journey. (Not yet implemented.)"
    return True, ""


def _best_party_skill(caller, skill_key):
    """Return the highest mastery level for skill_key across caller + party."""
    best = caller.get_skill_mastery(skill_key) if hasattr(caller, 'get_skill_mastery') else 0
    leader = caller.get_group_leader()
    if leader and leader.location == caller.location:
        best = max(best, leader.get_skill_mastery(skill_key) if hasattr(leader, 'get_skill_mastery') else 0)
    for f in (leader.get_followers(same_room=True) if leader else []):
        best = max(best, f.get_skill_mastery(skill_key) if hasattr(f, 'get_skill_mastery') else 0)
    return best


def _check_boat_level(caller, conditions):
    req = conditions.get("boat_level")
    if req:
        from typeclasses.items.untakeables.ship_nft_item import ShipNFTItem
        from enums.mastery_level import MasteryLevel
        best_tier = max(
            (obj.ship_tier for obj in caller.contents if isinstance(obj, ShipNFTItem)),
            default=0,
        )
        if best_tier < req:
            needed = MasteryLevel(req).name
            if best_tier == 0:
                return False, f"You need at least a {needed}-tier ship for this voyage. You don't own any ships."
            have = MasteryLevel(best_tier).name
            return False, f"You need at least a {needed}-tier ship for this voyage. Your best ship is {have}-tier."
    return True, ""


def _check_food(caller, conditions):
    cost = conditions.get("food_cost")
    if cost:
        have = caller.get_resource(BREAD_RESOURCE_ID)
        if have < cost:
            return False, f"This journey requires {cost} bread. You have {have}."
    return True, ""


def _check_gold(caller, conditions):
    cost = conditions.get("gold_cost")
    if cost:
        have = caller.get_gold()
        if have < cost:
            return False, f"This journey costs {cost} gold. You have {have}."
    return True, ""


CONDITION_CHECKS = [
    _check_level,
    _check_mounted,
    _check_fly,
    _check_water_breathing,
    _check_boat_level,
    _check_food,
    _check_gold,
]


def validate_conditions(caller, conditions):
    """Run all condition checks. Returns (ok, first_failure_message)."""
    for check in CONDITION_CHECKS:
        ok, msg = check(caller, conditions)
        if not ok:
            return False, msg
    return True, ""


def consume_costs(caller, conditions):
    """Consume food and gold costs after validation passes."""
    food_cost = conditions.get("food_cost")
    if food_cost:
        caller._remove_resource(BREAD_RESOURCE_ID, food_cost)

    gold_cost = conditions.get("gold_cost")
    if gold_cost:
        caller.return_gold_to_sink(gold_cost)


def is_destination_visible(caller, dest, gateway):
    """
    Check if a destination is visible to the caller or their party.

    Visibility rules (hidden defaults to True):
    1. hidden=False → always visible (test routes, non-gated destinations)
    2. Route map NFT in caller or party member inventory → visible
    3. Chart item (boss loot) with matching discover_item_tag → visible
    """
    if not dest.get("hidden", True):
        return True

    dest_key = dest.get("key", "")
    gateway_key = gateway.key
    route_key = f"{gateway_key}:{dest_key}"

    # Check caller + party for a route map NFT matching this route
    from typeclasses.items.maps.route_map_nft_item import RouteMapNFTItem
    party = _get_party_members(caller)
    for member in party:
        for obj in member.contents:
            if isinstance(obj, RouteMapNFTItem) and obj.route_key == route_key:
                return True

    # Check for chart item (boss loot) in caller inventory
    item_tag = dest.get("discover_item_tag")
    if item_tag:
        for member in party:
            for obj in member.contents:
                if obj.tags.get(item_tag, category="chart"):
                    return True

    return False


def _get_party_members(caller):
    """Return caller + group members in the same room."""
    members = [caller]
    if hasattr(caller, "get_group_leader"):
        leader = caller.get_group_leader()
        if leader:
            members = [leader] + leader.get_followers(same_room=True)
            if caller not in members:
                members.append(caller)
    return members


class CmdTravel(Command):
    """
    Travel to another zone via this gateway.

    Usage:
        travel                  — list destinations or travel if only one
        travel <destination>    — travel to a named destination
    """

    key = "travel"
    locks = "cmd:all()"
    help_category = "Travel"

    def func(self):
        caller = self.caller
        room = caller.location

        destinations = room.destinations if hasattr(room, "destinations") else []
        if not destinations:
            caller.msg("This gateway has no destinations configured.")
            return

        # Filter to visible destinations
        visible = [d for d in destinations if is_destination_visible(caller, d, room)]

        if not visible:
            caller.msg("You don't know of any destinations from here.")
            return

        # If args given, match to a destination
        if self.args.strip():
            search = self.args.strip().lower()
            match = None
            for d in visible:
                if d.get("key", "").lower() == search or d.get("label", "").lower().startswith(search):
                    match = d
                    break
            if not match:
                caller.msg(f"No known destination matching '{self.args.strip()}'.")
                return
            self._do_travel(caller, room, match)
            return

        # No args — auto-travel if single destination, else list
        if len(visible) == 1:
            self._do_travel(caller, room, visible[0])
            return

        # List destinations
        caller.msg("\n|c--- Available Destinations ---|n")
        for d in visible:
            label = d.get("label", d.get("key", "???"))
            conditions = d.get("conditions", {})
            reqs = self._format_requirements(caller, conditions)
            caller.msg(f"  |w{label}|n ({d.get('key', '')}){reqs}")
        caller.msg("\nUse |wtravel <destination>|n to depart.")

    def _format_requirements(self, caller, conditions):
        """Format requirement summary for listing."""
        parts = []
        if conditions.get("level_required"):
            parts.append(f"Level {conditions['level_required']}")
        if conditions.get("food_cost"):
            parts.append(f"{conditions['food_cost']} bread")
        if conditions.get("gold_cost"):
            parts.append(f"{conditions['gold_cost']} gold")
        if conditions.get("mounted"):
            parts.append("mount required")
        if conditions.get("fly"):
            parts.append("flying required")
        if conditions.get("boat_level"):
            from enums.mastery_level import MasteryLevel
            tier_name = MasteryLevel(conditions["boat_level"]).name
            parts.append(f"{tier_name}-tier ship")
        if not parts:
            return ""
        return " — " + ", ".join(parts)

    def _do_travel(self, caller, room, dest):
        """Validate conditions, consume costs, and teleport with delay."""
        if caller.ndb.is_processing:
            caller.msg("You are already busy. Wait until your current task finishes.")
            return

        conditions = dest.get("conditions", {})

        # Validate
        ok, msg = validate_conditions(caller, conditions)
        if not ok:
            caller.msg(msg)
            return

        destination_room = dest.get("destination")
        if not destination_room:
            caller.msg("This destination's gateway is not connected.")
            return

        # Consume costs upfront
        consume_costs(caller, conditions)

        # Narrative
        travel_desc = dest.get("travel_description", "You set off on your journey...")
        caller.msg(f"\n{travel_desc}")

        def _arrive():
            caller.move_to(destination_room, quiet=True, move_type="teleport")
            destination_room.msg_contents(
                f"{caller.key} arrives from their journey.",
                exclude=[caller],
            )

        _delayed_travel(caller, room, dest, _TRAVEL_MESSAGES, _arrive)

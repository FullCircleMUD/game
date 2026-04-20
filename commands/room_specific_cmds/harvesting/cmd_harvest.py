"""
Harvest command — gather raw resources one at a time.

Available in harvesting rooms (mines, forests, fields, etc.). Each room is
configured with a single resource type and a matching command. Only the
correct command works in each room (mine in mines, chop in forests, etc.).

Usage:
    mine        — mine ore in a mine
    chop        — chop wood in a forest
    harvest     — harvest crops in a field
    forage      — forage for materials
    gather      — gather resources
    pick        — pick items

Each action takes 3 seconds and yields 1 unit of the room's resource.
Players don't know how many resources remain — they keep gathering until
the room is depleted.
"""

from evennia import Command
from evennia.utils import delay

from blockchain.xrpl.currency_cache import get_resource_type
from commands.command import FCMCommandMixin


# ── Easy-to-change delay for harvesting ──
HARVEST_DELAY_SECONDS = 3

_CANONICAL = {
    "harvest": "harvest",
    "mine": "mine",
    "chop": "chop",
    "forage": "forage",
    "gather": "gather",
    "pick": "pick",
}

_GERUNDS = {
    "harvest": "harvesting",
    "mine": "mining",
    "chop": "chopping",
    "forage": "foraging",
    "gather": "gathering",
    "pick": "picking",
}


class CmdHarvest(FCMCommandMixin, Command):
    """
    Gather resources from this location.

    Usage:
        mine / chop / harvest / hunt / fish / forage

    Each action takes a few seconds and yields 1 unit of the room's
    resource. Keep gathering until the area is depleted.
    """

    key = "harvest"
    aliases = ["chop", "mine", "forage", "gather", "pick"]
    
    locks = "cmd:all()"
    help_category = "Gathering"

    def func(self):
        caller = self.caller
        room = caller.location
        canonical = _CANONICAL.get(self.cmdstring, self.cmdstring)

        # --- Wrong command for this room ---
        if canonical != room.harvest_command:
            caller.msg(f"You can't {canonical} here.")
            return

        # --- Busy check (shared with process/craft) ---
        if caller.ndb.is_processing:
            caller.msg("You are busy. Wait until you finish what you're doing.")
            return

        # --- Height check ---
        if caller.room_vertical_position != room.harvest_height:
            if room.harvest_height > 0:
                caller.msg(
                    "The resource is above you. You need to fly up to reach it."
                )
            elif room.harvest_height < 0:
                caller.msg(
                    "The resource is below the water. You need to swim down to reach it."
                )
            else:
                caller.msg("You need to be on the ground to do that.")
            return

        # --- Depleted check ---
        if room.resource_count <= 0:
            caller.msg(room.desc_depleted)
            return

        # --- Tool check ---
        if room.required_tool:
            if not any(obj.key == room.required_tool for obj in caller.contents):
                caller.msg(
                    f"You need a {room.required_tool} to {canonical} here."
                )
                return

        # --- Resolve resource name ---
        rt = get_resource_type(room.resource_id)
        resource_name = rt["name"] if rt else f"Resource #{room.resource_id}"
        gerund = _GERUNDS.get(canonical, "gathering")

        # --- Lock and start ---
        caller.ndb.is_processing = True
        caller.msg(f"You begin {gerund}...")
        caller.location.msg_contents(
            f"{caller.key} begins {gerund}.",
            exclude=[caller],
            from_obj=caller,
        )

        # --- Delayed completion ---
        def _complete():
            # Re-check count at completion (another player may have taken the last one)
            if room.resource_count <= 0:
                caller.msg(f"There is nothing left to {canonical}.")
                caller.ndb.is_processing = False
                return

            room.resource_count -= 1
            caller.receive_resource_from_reserve(room.resource_id, 1)
            caller.msg(f"|gYou {canonical} 1 {resource_name}.|n")

            # Award XP if configured
            xp = room.harvest_xp
            if xp and xp > 0:
                caller.at_gain_experience_points(xp)

            caller.ndb.is_processing = False

        delay(HARVEST_DELAY_SECONDS, _complete)

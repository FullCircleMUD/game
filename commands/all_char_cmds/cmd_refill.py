"""
Refill command — top up a water container from a water source in the room.

Usage:
    refill <container> <source>
    fill <container> <source>

Both arguments are required. The container must be a water container
in inventory, the source must be a water source fixture in the room
(fountain, well, spring, etc).
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


class CmdRefill(FCMCommandMixin, Command):
    """
    Refill a water container from a water source in the room.

    Usage:
        refill <container> <source>
        fill <container> <source>

    Examples:
        refill canteen fountain
        fill waterskin well
    """

    key = "refill"
    aliases = ("fill",)
    locks = "cmd:all()"
    help_category = "Items"

    def parse(self):
        parts = self.args.strip().split(None, 1)
        self.container_name = parts[0] if parts else ""
        self.source_name = parts[1] if len(parts) > 1 else ""

    def func(self):
        caller = self.caller

        if not self.container_name or not self.source_name:
            caller.msg("Usage: refill <container> <source>")
            return

        room = caller.location
        if not room:
            return

        # Darkness — can't see what you're doing
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        # Find container in inventory
        container, _ = resolve_target(
            caller, self.container_name, "items_inventory",
            extra_predicates=(p_can_see,),
        )
        if not container:
            caller.msg(
                f"You don't see '{self.container_name}' in your inventory."
            )
            return

        if not getattr(container, "is_water_container", False):
            caller.msg(f"You can't refill {container.key}.")
            return

        # Find water source in room
        source, _ = resolve_target(
            caller, self.source_name, "items_room_nonexit",
            extra_predicates=(p_can_see,),
        )
        if not source:
            caller.msg(f"You don't see '{self.source_name}' here.")
            return

        if not getattr(source, "is_water_source", False):
            caller.msg(f"You can't refill from {source.key}.")
            return

        # Refill
        success, msg = container.refill_to_full()
        if not success:
            caller.msg(msg)
            return

        caller.msg(f"|cYou refill {container.key} at {source.key}.|n")
        if caller.location:
            caller.location.msg_contents(
                f"$You() $conj(refill) {container.key} at {source.key}.",
                from_obj=caller,
                exclude=[caller],
            )

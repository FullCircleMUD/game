"""
Close command — close a closeable object (chest, door) in the room.

Usage:
    close <target>
    close <target> <direction>
    close <direction>
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.direction_parser import parse_direction
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see, p_is_openable, p_same_height


class CmdClose(FCMCommandMixin, Command):
    """
    Close a chest, door, or other closeable object.

    Usage:
        close <target>
        close <direction>
        close <target> <direction>
    """

    key = "close"
    aliases = []
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Close what?")
            return

        # Darkness — can't identify what to close without sight
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        target_str = self.args.strip()
        parsed_name, direction = parse_direction(target_str)

        if direction:
            # Direction parsed — targeting an exit specifically.
            # Room objects and inventory not searched because
            # directional qualifiers only apply to exits.
            target, _ = resolve_target(
                caller, parsed_name, "items_room_exit_by_direction",
                extra_predicates=(p_can_see,), direction=direction,
            )
        else:
            # No direction — broad search: exits, room objects, inventory.
            target, _ = resolve_target(
                caller, target_str, "items_room_all_then_inventory",
                extra_predicates=(p_can_see,),
            )

        if not target:
            caller.msg(f"You don't see '{target_str}' here.")
            return

        # Height check — room objects must be at same height
        if target.location != caller and not p_same_height(caller)(target, caller):
            caller.msg(f"{target.key} is out of reach.")
            return

        if not p_is_openable(target, caller):
            caller.msg("You can't close that.")
            return

        success, msg = target.close(caller)
        caller.msg(msg)

        if success and caller.location:
            caller.location.msg_contents(
                f"$You() $conj(close) {target.key}.",
                from_obj=caller, exclude=[caller],
            )

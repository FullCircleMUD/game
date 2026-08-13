"""
Lock command — lock a lockable object (chest, door) in the room.

Usage:
    lock <target>
    lock <target> <direction>
    lock <direction>
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.direction_parser import parse_direction
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see, p_is_lockable, p_same_height
from utils.visibility import looker_is_blind


class CmdLock(FCMCommandMixin, Command):
    """
    Lock a chest, door, or other lockable object.

    Usage:
        lock <target>
        lock <direction>
        lock <target> <direction>

    The object must be closed first.
    """

    key = "lock"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Lock what?")
            return

        target_str = self.args.strip()

        # Lining a key up with a keyhole needs eyes, so this one refuses
        # rather than costing time. Say why — "you don't see it here"
        # reads as absent when the lock is right in front of them.
        if looker_is_blind(caller):
            caller.msg(f"It's too dark to make out '{target_str}'.")
            return

        parsed_name, direction = parse_direction(target_str)

        if direction:
            target, _ = resolve_target(
                caller, parsed_name, "items_room_exit_by_direction",
                extra_predicates=(p_can_see,), direction=direction,
            )
        else:
            target, _ = resolve_target(
                caller, target_str, "items_room_all_then_inventory",
                extra_predicates=(p_can_see,),
            )

        if not target:
            caller.msg(f"You don't see '{target_str}' here.")
            return
        if target.location != caller and not p_same_height(caller)(target, caller):
            caller.msg(f"{target.key} is out of reach.")
            return
        if not p_is_lockable(target, caller):
            caller.msg("You can't lock that.")
            return

        success, msg = target.lock(caller)
        caller.msg(msg)

        if success and caller.location:
            caller.location.msg_contents(
                f"$You() $conj(lock) {target.key}.",
                from_obj=caller, exclude=[caller],
            )

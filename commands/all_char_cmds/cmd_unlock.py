"""
Unlock command — unlock a locked object using a key from inventory.

Usage:
    unlock <target>
    unlock <target> <direction>
    unlock <direction>

Searches the character's inventory for a KeyItem whose key_tag
matches the target's key_tag. If found, consumes the key and unlocks.
For lockpicking without a key, use the 'picklock' skill command.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.world_objects.key_item import KeyItem
from utils.direction_parser import parse_direction
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import (
    p_can_see, p_is_lockable, p_is_locked, p_same_height,
)


class CmdUnlock(FCMCommandMixin, Command):
    """
    Unlock a chest, door, or other locked object using a key.

    Usage:
        unlock <target>
        unlock <direction>
        unlock <target> <direction>

    You must have the correct key in your inventory.
    To pick a lock without a key, use 'picklock'.
    """

    key = "unlock"
    locks = "cmd:all()"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Unlock what?")
            return

        # Darkness
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        target_str = self.args.strip()
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
            caller.msg("You can't unlock that.")
            return
        if not p_is_locked(target, caller):
            caller.msg(f"{target.key} is not locked.")
            return

        # Find a matching key in inventory
        key_item = self._find_matching_key(caller, target)
        if not key_item:
            caller.msg(
                f"You don't have a key that fits {target.key}."
            )
            return

        success, msg = target.unlock(caller, key_item)
        caller.msg(msg)

        if success and caller.location:
            caller.location.msg_contents(
                f"$You() $conj(unlock) {target.key}.",
                from_obj=caller, exclude=[caller],
            )

    def _find_matching_key(self, caller, target):
        """Search caller's inventory for a KeyItem matching the target's key_tag."""
        target_tag = getattr(target, "key_tag", None)
        if not target_tag:
            return None

        for obj in caller.contents:
            if isinstance(obj, KeyItem):
                if getattr(obj, "key_tag", None) == target_tag:
                    return obj
        return None

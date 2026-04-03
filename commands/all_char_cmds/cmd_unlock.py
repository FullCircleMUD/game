"""
Unlock command — unlock a locked object using a key from inventory.

Usage:
    unlock <target>

Searches the character's inventory for a KeyItem whose key_tag
matches the target's key_tag. If found, consumes the key and unlocks.
For lockpicking without a key, use the 'picklock' skill command.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.world_objects.key_item import KeyItem
from utils.find_exit_target import find_exit_target


class CmdUnlock(FCMCommandMixin, Command):
    """
    Unlock a chest, door, or other locked object using a key.

    Usage:
        unlock <target>

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

        target_name = self.args.strip()

        target = find_exit_target(caller, target_name)
        if not target:
            return

        if not hasattr(target, "unlock") or not hasattr(target, "is_locked"):
            caller.msg("You can't unlock that.")
            return

        if not target.is_locked:
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

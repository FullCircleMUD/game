"""
Lock command — lock a closeable object (chest, door) in the room.

Usage:
    lock <target>
"""

from evennia import Command

from utils.find_exit_target import find_exit_target


class CmdLock(Command):
    """
    Lock a chest, door, or other lockable object.

    Usage:
        lock <target>

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

        target_name = self.args.strip()

        target = find_exit_target(caller, target_name)
        if not target:
            return

        if not hasattr(target, "lock") or not hasattr(target, "is_locked"):
            caller.msg("You can't lock that.")
            return

        success, msg = target.lock(caller)
        caller.msg(msg)

        if success and caller.location:
            caller.location.msg_contents(
                f"$You() $conj(lock) {target.key}.",
                from_obj=caller, exclude=[caller],
            )

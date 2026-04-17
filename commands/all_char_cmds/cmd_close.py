"""
Close command — close a closeable object (chest, door) in the room.

Usage:
    close <target>
"""

from evennia import Command

from commands.command import FCMCommandMixin
from utils.find_exit_target import find_exit_target


class CmdClose(FCMCommandMixin, Command):
    """
    Close a chest, door, or other closeable object.

    Usage:
        close <target>
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

        target_name = self.args.strip()

        target = find_exit_target(caller, target_name)
        if not target:
            return

        if not hasattr(target, "close"):
            caller.msg("You can't close that.")
            return

        success, msg = target.close(caller)
        caller.msg(msg)

        if success and caller.location:
            caller.location.msg_contents(
                f"$You() $conj(close) {target.key}.",
                from_obj=caller, exclude=[caller],
            )

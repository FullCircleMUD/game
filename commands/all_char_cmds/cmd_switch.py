"""
CmdSwitch — interact with toggleable switch fixtures.

Usage:
    pull <target>
    push <target>
    turn <target>
    flip <target>

Finds a SwitchMixin object in the room and toggles it. If the
switch is inactive, activates it. If already active, deactivates
it (unless can_deactivate is False).
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdSwitch(FCMCommandMixin, Command):
    """
    Interact with a lever, button, or switch.

    Usage:
        pull <target>
        push <target>
        turn <target>
        flip <target>

    Toggles a switch in the room — pull a lever, push a button,
    turn a valve.
    """

    key = "pull"
    aliases = ("push", "flip", "press")
    locks = "cmd:all()"
    arg_regex = r"\s|$"
    help_category = "General"

    def parse(self):
        self.target_name = self.args.strip()

    def func(self):
        caller = self.caller

        if not self.target_name:
            caller.msg("Pull what?")
            return

        room = caller.location
        if not room:
            return

        # Find switchable fixtures in the room
        switches = [
            obj for obj in room.contents
            if hasattr(obj, "is_activated")
            and hasattr(obj, "activate")
        ]

        if not switches:
            caller.msg("There's nothing here to pull, push, or turn.")
            return

        # Search for the target
        target = caller.search(
            self.target_name, location=room, quiet=True,
        )
        if not target:
            caller.msg(f"You don't see '{self.target_name}' here.")
            return
        if isinstance(target, list):
            target = target[0]

        if not hasattr(target, "activate"):
            caller.msg(f"You can't do that with {target.key}.")
            return

        # Toggle
        if target.is_activated:
            target.deactivate(caller)
        else:
            target.activate(caller)

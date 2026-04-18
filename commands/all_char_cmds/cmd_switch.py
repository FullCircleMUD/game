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
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


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

        # Darkness — can't interact with what you can't see
        if hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        target, _ = resolve_target(
            caller, self.target_name, "items_room_nonexit",
            extra_predicates=(p_can_see,),
        )
        if not target:
            caller.msg(f"You don't see '{self.target_name}' here.")
            return

        if not hasattr(target, "activate"):
            caller.msg(f"You can't do that with {target.key}.")
            return

        # Toggle
        if target.is_activated:
            target.deactivate(caller)
        else:
            target.activate(caller)

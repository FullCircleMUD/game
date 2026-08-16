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
from utils.busy import (
    FUMBLE_BUSY_MESSAGE,
    FUMBLE_MOVE_MESSAGE,
    check_busy,
    fumble_seconds,
    start_busy,
)
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_perceive
from utils.visibility import looker_is_blind


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

        if check_busy(caller):
            return

        # No sight check — a lever is found by running your hands along
        # the wall, and nothing about pulling it needs eyes once you have
        # hold of it. Sightlessness costs the time. The search runs
        # before the outcome is known, so a bare wall costs the same.
        #
        # Undiscovered hidden switches stay out of reach: p_can_perceive
        # filters them, so groping about cannot stumble onto a secret
        # lever that a sighted character would have had to search for.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._switch(caller),
                self_msg="You feel along in the dark, hunting for something to pull...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._switch(caller)

    def _switch(self, caller):
        """Find the switch and toggle it. Success or failure both."""
        target, _ = resolve_target(
            caller, self.target_name, "items_room_nonexit",
            extra_predicates=(p_can_perceive,),
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

"""
'go' prefix for movement — redirects to the bare direction command.

Players (especially new ones) instinctively type 'go north' instead
of bare 'north'. This command strips the 'go' prefix and executes
the direction as a command, which matches the exit.

Usage:
    go <direction>
    go north
    go south
"""

from evennia.utils import utils

from commands.command import FCMCommandMixin

COMMAND_DEFAULT_CLASS = utils.class_from_module(
    "evennia.commands.default.muxcommand.MuxCommand"
)


class CmdGo(FCMCommandMixin, COMMAND_DEFAULT_CLASS):
    """
    Move in a direction.

    Usage:
        go <direction>

    Shortcut for typing the direction name directly.
    For example, 'go north' is the same as typing 'north'.
    """

    key = "go"
    locks = "cmd:all()"
    help_category = "General"
    arg_regex = r"\s|$"

    def func(self):
        if not self.args or not self.args.strip():
            self.msg("Go where? Try 'go north', 'go south', etc.")
            return

        direction = self.args.strip()
        self.caller.execute_cmd(direction)

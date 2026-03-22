"""
CmdConsider — gauge how tough a target is before fighting.

Compares your level to the target's level and gives a graduated
difficulty message, matching CircleMUD's classic consider command.

Usage:
    consider <target>
"""

from evennia import Command


def _get_consider_message(diff):
    """Return a difficulty message based on level difference (target - caller)."""
    if diff <= -10:
        return "|gNow where did that chicken go?|n"
    elif diff <= -5:
        return "|gYou could do it with a needle!|n"
    elif diff <= -2:
        return "|gEasy.|n"
    elif diff <= -1:
        return "|gFairly easy.|n"
    elif diff == 0:
        return "|yThe perfect match!|n"
    elif diff <= 1:
        return "|yYou would need some luck!|n"
    elif diff <= 2:
        return "|yYou would need a lot of luck!|n"
    elif diff <= 3:
        return "|rYou would need a lot of luck and great equipment!|n"
    elif diff <= 5:
        return "|rDo you feel lucky, punk?|n"
    elif diff <= 10:
        return "|rAre you mad!?|n"
    else:
        return "|rYou ARE mad!|n"


class CmdConsider(Command):
    """
    Gauge how tough a target is.

    Usage:
        consider <target>

    Compares your level to the target's and gives a rough
    estimate of how difficult a fight would be.
    """

    key = "consider"
    aliases = ["con"]
    help_category = "Combat"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Consider who?")
            return

        target = caller.search(self.args.strip())
        if not target:
            return

        if not hasattr(target, "get_level"):
            caller.msg("You can't consider that.")
            return

        diff = target.get_level() - caller.get_level()
        message = _get_consider_message(diff)
        caller.msg(f"{target.key}: {message}")

"""
CmdWimpy — set an HP threshold for automatic fleeing.

When your HP drops below the wimpy threshold during combat,
you automatically flee through a random exit (guaranteed escape).

Usage:
    wimpy              — show current setting
    wimpy <hp>         — set wimpy threshold (max 50% of your max HP)
    wimpy off          — disable wimpy
"""

from evennia import Command


class CmdWimpy(Command):
    """
    Set an auto-flee HP threshold.

    Usage:
        wimpy              — show current setting
        wimpy <hp>         — set wimpy threshold
        wimpy off          — disable wimpy

    When your HP drops below the wimpy threshold during combat,
    you automatically flee through a random exit. The flee is
    guaranteed (no DEX check).

    The threshold cannot exceed 50% of your maximum HP.
    """

    key = "wimpy"
    help_category = "Combat"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            self._show_wimpy(caller)
            return

        if args.lower() in ("off", "0"):
            caller.wimpy_threshold = 0
            caller.msg("|yWimpy disabled.|n")
            return

        try:
            value = int(args)
        except ValueError:
            caller.msg("Usage: wimpy <hp> | wimpy off")
            return

        if value < 0:
            caller.msg("Wimpy threshold must be a positive number.")
            return

        max_allowed = caller.effective_hp_max // 2
        if value > max_allowed:
            caller.msg(
                f"Wimpy threshold can't exceed 50% of your max HP "
                f"({max_allowed})."
            )
            return

        caller.wimpy_threshold = value
        caller.msg(f"|yWimpy set to {value} HP.|n")

    def _show_wimpy(self, caller):
        threshold = caller.wimpy_threshold
        if threshold <= 0:
            caller.msg("Wimpy is currently |yoff|n.")
        else:
            caller.msg(
                f"Wimpy is set to |y{threshold} HP|n "
                f"(max HP: {caller.effective_hp_max})."
            )

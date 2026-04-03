"""
Smite command — convenience alias for ``toggle smite``.

Typing ``smite`` toggles reactive Smite on/off, same as ``toggle smite``.
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdSmite(FCMCommandMixin, Command):
    """
    Toggle reactive Smite on/off.

    Usage:
        smite

    While active, every weapon hit you land in combat channels holy
    radiance through your weapon, adding bonus radiant damage. Each
    hit costs mana — Smite stops firing when you run out.

    Requires Smite to be memorised.
    This is a convenience alias for 'toggle smite'.
    """

    key = "smite"
    aliases = ["smi"]
    help_category = "Combat"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        result = caller.toggle_preference("smite")
        if result is None:
            caller.msg("Unknown preference 'smite'.")
            return
        name, new_val = result
        if name is None:
            # Gate failure — new_val is the error message
            caller.msg(new_val)
            return
        status = "|gON|n" if new_val else "|rOFF|n"
        caller.msg(f"smite is now {status}.")

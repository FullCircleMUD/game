"""
Shield command — convenience alias for ``toggle shield``.

Typing ``shield`` toggles reactive Shield on/off, same as ``toggle shield``.
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdShield(FCMCommandMixin, Command):
    """
    Toggle reactive Shield on/off.

    Usage:
        shield

    While active, Shield triggers automatically when you are about
    to be hit in combat, granting a temporary AC bonus. Each trigger
    costs mana.

    Requires Shield to be memorised.
    This is a convenience alias for 'toggle shield'.
    """

    key = "shield"
    aliases = []
    help_category = "Combat"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        result = caller.toggle_preference("shield")
        if result is None:
            caller.msg("Unknown preference 'shield'.")
            return
        name, new_val = result
        if name is None:
            # Gate failure — new_val is the error message
            caller.msg(new_val)
            return
        status = "|gON|n" if new_val else "|rOFF|n"
        caller.msg(f"shield is now {status}.")

"""
AFK command — convenience shortcut for 'toggle afk'.

Usage:
    afk
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdAfk(FCMCommandMixin, Command):
    """
    Toggle your AFK status.

    Usage:
        afk

    Marks you as away from keyboard. Others will see (AFK) next to
    your name in the room and in the who list, and will be notified
    if they speak to you directly.
    """

    key = "afk"
    locks = "cmd:all()"
    help_category = "System"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller
        result = caller.toggle_preference("afk")
        if result is None:
            caller.msg("AFK preference not available.")
            return
        key, new_val = result
        status = "|gON|n" if new_val else "|rOFF|n"
        caller.msg(f"AFK: {status}")

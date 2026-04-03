"""
CmdTutorial — per-room tutorial instruction display.

Available in every tutorial room. Reads the room's db.tutorial_text
attribute and displays it with formatting.
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdTutorial(FCMCommandMixin, Command):
    """
    View the tutorial instructions for this room.

    Usage:
        tutorial
        tut

    Each room in the tutorial teaches a different game mechanic.
    Use this command to see what to learn and practice here.
    """

    key = "tutorial"
    aliases = ["tut"]
    locks = "cmd:all()"
    help_category = "Tutorial"
    arg_regex = r"\s|$"

    def func(self):
        room = self.caller.location
        text = room.db.tutorial_text
        if not text:
            self.caller.msg("No tutorial information for this room.")
            return

        sep = "|c" + "=" * 60 + "|n"
        self.caller.msg(f"\n{sep}")
        self.caller.msg(text)
        self.caller.msg(f"{sep}\n")

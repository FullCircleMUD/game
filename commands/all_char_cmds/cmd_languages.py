"""
Languages command — check what languages you speak.

Usage:
    languages
    lang
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdLanguages(FCMCommandMixin, Command):
    """
    Check what languages you speak.

    Usage:
        languages
        lang
    """

    key = "languages"
    aliases = ["lang"]
    locks = "cmd:all()"
    help_category = "Character"
    arg_regex = r"\s|$"
    allow_while_sleeping = True

    def func(self):
        langs = self.caller.db.languages
        if not langs:
            self.msg("You don't speak any languages.")
            return
        sorted_langs = sorted(lang.capitalize() for lang in langs)
        self.msg("You speak: " + ", ".join(sorted_langs) + ".")

"""
Prompt command — view or customise the status prompt format.

Usage:
    prompt              — show current format and available tokens
    prompt <format>     — set a custom prompt format
    prompt default      — reset to default format
"""

from evennia import Command

from commands.command import FCMCommandMixin


DEFAULT_PROMPT = "%hH %mM %vV > "

TOKEN_HELP = (
    "|wAvailable tokens:|n\n"
    "  %h  Current HP        %H  Max HP\n"
    "  %m  Current Mana      %M  Max Mana\n"
    "  %v  Current Move      %V  Max Move\n"
    "  %g  Gold carried      %x  XP\n"
    "  %l  Level"
)


class CmdPrompt(FCMCommandMixin, Command):
    """
    View or customise your status prompt.

    Usage:
        prompt              — show current format and token list
        prompt <format>     — set a custom prompt format
        prompt default      — reset to default

    Example:
        prompt %hH %mM %vV >
        prompt [%h/%H HP] [%m/%M MP] %g gold >

    Use 'toggle prompt' to turn the prompt on or off.
    """

    key = "prompt"
    locks = "cmd:all()"
    help_category = "System"

    def func(self):
        caller = self.caller
        args = self.args.strip()

        if not args:
            fmt = caller.prompt_format or DEFAULT_PROMPT
            caller.msg(f"|wCurrent prompt format:|n {fmt}")
            caller.msg(f"|wPreview:|n {caller.get_prompt()}")
            caller.msg(TOKEN_HELP)
            return

        if args.lower() == "default":
            caller.prompt_format = DEFAULT_PROMPT
            caller.msg(f"Prompt reset to default: {DEFAULT_PROMPT}")
            return

        caller.prompt_format = args
        caller.msg(f"Prompt set to: {args}")
        caller.msg(f"|wPreview:|n {caller.get_prompt()}")

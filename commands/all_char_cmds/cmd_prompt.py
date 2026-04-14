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
    "|wVitals:|n\n"
    "  %h  Current HP        %H  Max HP\n"
    "  %m  Current Mana      %M  Max Mana\n"
    "  %v  Current Move      %V  Max Move\n"
    "\n"
    "|wAutowarn (forced colour):|n\n"
    "  %i  HP                %n  Mana\n"
    "  %w  Move              %s  Self status (e.g. \"wounded\")\n"
    "\n"
    "|wCharacter / World:|n\n"
    "  %g  Gold carried      %x  XP\n"
    "  %l  Level             %a  Armor class\n"
    "  %A  Alignment         %C  Current position\n"
    "  %T  Time of day       %r  Newline\n"
    "\n"
    "|wBattle only (empty outside combat):|n\n"
    "  %f  Target name       %c  Target condition"
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
    allow_while_sleeping = True

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

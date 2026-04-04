"""
FCMCommandMixin — prompt refresh after every command.

This is a cooperative mixin, not a standalone base class. It adds an
at_post_cmd() hook that refreshes the player's text prompt and OOB
vitals after every command. It calls super().at_post_cmd() first so
any parent class logic (Evennia's Command, MuxCommand, ExitCommand,
etc.) is preserved.

Usage — add as the FIRST parent so MRO calls our at_post_cmd before
the Evennia base:

    from commands.command import FCMCommandMixin

    # For custom commands:
    class CmdFoo(FCMCommandMixin, Command):
        ...

    # For Evennia override commands:
    class CmdLook(FCMCommandMixin, _EvenniaCmdLook):
        ...

    # For exit commands:
    class _HeightAwareExitCommand(FCMCommandMixin, ExitCommand):
        ...

The mixin is deliberately lightweight — no __init__, no parse(), no
class attributes. It won't interfere with any parent regardless of
whether that parent is Command, MuxCommand, or ExitCommand.
"""


class FCMCommandMixin:
    """Mixin that refreshes the player prompt after every command.

    Only fires for puppeted characters (has get_prompt). Accounts
    at the main menu, session-level commands, and NPCs are skipped.

    Subclasses that should work while sleeping set:
        allow_while_sleeping = True
    """

    allow_while_sleeping = False

    def at_pre_cmd(self):
        """Block commands while sleeping unless explicitly allowed."""
        if (
            not self.allow_while_sleeping
            and getattr(self.caller, "position", None) == "sleeping"
        ):
            self.caller.msg(
                "You can't do that while asleep. Try |wstand|n or |wwake|n."
            )
            return True  # abort command
        return super().at_pre_cmd()

    def at_post_cmd(self):
        """Chain to parent at_post_cmd, then refresh prompt."""
        super().at_post_cmd()
        caller = self.caller
        if not hasattr(caller, "get_prompt"):
            return
        if hasattr(caller, "send_vitals_update"):
            caller.send_vitals_update()
        if getattr(caller, "prompt_active", True):
            caller.msg(prompt=caller.get_prompt())

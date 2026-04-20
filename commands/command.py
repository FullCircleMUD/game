"""
FCMCommandMixin — inline command echo + OOB vitals refresh.

This is a cooperative mixin, not a standalone base class. It adds an
at_pre_cmd() hook that echoes the typed command back to the player
inline (DikuMUD style) and an at_post_cmd() hook that refreshes the
OOB vitals panel. The trailing scrollback prompt is handled by
FCMCharacter.msg() so unsolicited output gets one too.

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
                "In your dreams or what? Try |wstand|n or |wwake|n."
            )
            return True  # abort command
        from twisted.internet import reactor

        caller = self.caller
        raw = (self.raw_string or "").rstrip("\r\n")
        if (
            reactor.running
            and raw
            and hasattr(caller, "get_prompt")
            and getattr(caller, "prompt_active", True)
        ):
            # Echo typed command inline. Flag the debounce so the msg()
            # override doesn't queue a bare prompt for this echo line —
            # the next real output from the command will re-queue.
            caller.ndb._prompt_scheduled = True
            caller.msg(f"{caller.get_prompt()}> {raw}")
            caller.ndb._prompt_scheduled = False
        return super().at_pre_cmd()

    def at_post_cmd(self):
        """Chain to parent at_post_cmd, then refresh OOB vitals panel."""
        super().at_post_cmd()
        caller = self.caller
        if hasattr(caller, "send_vitals_update"):
            caller.send_vitals_update()

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

    Subclasses that demand a posture set one pose or several:
        required_position = "sitting"
        required_position = ("sitting", "resting")

    and may replace the refusal wording with:
        position_error_msg = "You must sit down to read a book."
    """

    allow_while_sleeping = False

    # The poses a command will accept, as a string or a tuple of them.
    # None means any pose will do, which is right for nearly every
    # command — look, say and inventory work sitting, standing or
    # fighting. Only the commands that genuinely need a body position
    # name one.
    required_position = None
    position_error_msg = None

    def _position_refusal(self):
        """The line a wrongly-posed character gets, or None if posed right."""
        required = self.required_position
        if not required:
            return None
        if isinstance(required, str):
            required = (required,)
        if getattr(self.caller, "position", None) in required:
            return None
        if self.position_error_msg:
            return self.position_error_msg
        poses = " or ".join(f"|w{pose}|n" for pose in required)
        return f"You must be {poses} to do that."

    def at_pre_cmd(self):
        """Block commands while sleeping or wrongly posed."""
        if (
            not self.allow_while_sleeping
            and getattr(self.caller, "position", None) == "sleeping"
        ):
            self.caller.msg(
                "In your dreams or what? Try |wstand|n or |wwake|n."
            )
            return True  # abort command

        refusal = self._position_refusal()
        if refusal:
            self.caller.msg(refusal)
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
        # caller = self.caller
        # if hasattr(caller, "send_vitals_update"):
        #     caller.send_vitals_update()

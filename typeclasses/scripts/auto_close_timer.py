"""
Auto-close timer — one-shot script that closes a closeable object after a delay.

Attached to any object with CloseableMixin. After the configured interval,
sets is_open = False and messages the room.

Independent of RelockTimerScript — if both are present, whichever fires
first handles the close; the other sees the door already closed and skips.
"""

from evennia import DefaultScript


class AutoCloseTimerScript(DefaultScript):
    """
    One-shot timer that closes its parent object.
    """

    def at_script_creation(self):
        self.key = "auto_close_timer"
        self.desc = "Auto-close countdown"
        self.persistent = True
        self.start_delay = True    # wait before first (and only) fire
        self.repeats = 1           # fire once then stop

    def at_repeat(self):
        obj = self.obj
        if not obj or not obj.pk:
            self.stop()
            return

        if hasattr(obj, "is_open") and obj.is_open:
            obj.is_open = False
            obj.at_close(None)

            if obj.location:
                obj.location.msg_contents(
                    f"|y{obj.key} swings shut.|n"
                )

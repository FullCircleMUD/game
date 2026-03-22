"""
Relock timer — one-shot script that re-locks a lockable object after a delay.

Attached to any object with LockableMixin. After the configured interval,
sets is_locked = True and messages the room.

Pattern follows BreathTimerScript: one-shot (repeat=False after first fire).
"""

from evennia import DefaultScript


class RelockTimerScript(DefaultScript):
    """
    One-shot timer that re-locks its parent object.
    """

    def at_script_creation(self):
        self.key = "relock_timer"
        self.desc = "Auto-relock countdown"
        self.persistent = True
        self.start_delay = True    # wait before first (and only) fire
        self.repeats = 1           # fire once then stop

    def at_repeat(self):
        obj = self.obj
        if not obj or not obj.pk:
            self.stop()
            return

        if hasattr(obj, "is_locked") and not obj.is_locked:
            obj.is_locked = True
            if hasattr(obj, "is_open") and obj.is_open:
                obj.is_open = False

            if obj.location:
                obj.location.msg_contents(
                    f"|y{obj.key} clicks shut and locks itself.|n"
                )

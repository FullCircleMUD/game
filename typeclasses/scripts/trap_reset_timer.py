"""
Trap reset timer — one-shot script that re-arms a trap after a delay.

Attached to any object with TrapMixin. After the configured interval,
sets trap_armed = True, trap_detected = False (trap resets and is hidden
again), and messages the room. Models magical traps that regenerate.

Pattern follows RelockTimerScript: one-shot (repeat=False after first fire).
"""

from evennia import DefaultScript


class TrapResetScript(DefaultScript):
    """
    One-shot timer that re-arms its parent trap.
    """

    def at_script_creation(self):
        self.key = "trap_reset_timer"
        self.desc = "Trap reset countdown"
        self.persistent = True
        self.start_delay = True    # wait before first (and only) fire
        self.repeats = 1           # fire once then stop

    def at_repeat(self):
        obj = self.obj
        if not obj or not obj.pk:
            self.stop()
            return

        if hasattr(obj, "is_trapped") and obj.is_trapped:
            obj.trap_armed = True
            obj.trap_detected = False

            room = None
            from typeclasses.terrain.rooms.room_base import RoomBase
            if isinstance(obj, RoomBase):
                room = obj
            elif hasattr(obj, "location"):
                room = obj.location

            if room:
                desc = getattr(obj, "trap_description", "a trap")
                room.msg_contents(
                    f"|yYou sense {desc} resetting itself...|n"
                )

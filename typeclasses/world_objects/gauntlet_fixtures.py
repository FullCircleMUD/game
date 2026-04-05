"""
Gauntlet fixtures — switch fixtures used in the Thieves' Gauntlet.

These must be importable typeclasses (not local classes in a builder)
so Evennia can resolve their typeclass path after a server restart.
"""

from typeclasses.world_objects.switch_fixture import SwitchFixture


class GauntletTrapLever(SwitchFixture):
    """A hidden lever that disarms a trap in the same room when activated."""

    def at_activate(self, caller):
        for obj in self.location.contents:
            if hasattr(obj, "trap_armed") and obj.trap_armed:
                obj.trap_armed = False
                msg_self = self.db.lever_activate_self_msg
                msg_room = self.db.lever_activate_room_msg
                if msg_self:
                    caller.msg(f"|g{msg_self}|n")
                if msg_room and self.location:
                    self.location.msg_contents(
                        f"{caller.key} {msg_room}",
                        exclude=[caller],
                        from_obj=caller,
                    )
                return
        caller.msg("Nothing seems to happen.")


class DeadSwitch(SwitchFixture):
    """A switch that does nothing — resets immediately after activation."""

    def at_activate(self, caller):
        msg = self.db.dead_switch_msg
        if msg:
            caller.msg(msg)
        # Reset immediately so the player can try again
        self.is_activated = False

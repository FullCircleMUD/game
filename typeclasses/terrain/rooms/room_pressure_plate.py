"""
PressurePlateRoom — a room with a pressure plate trap.

The first character to enter hears a "click" and is frozen in place.
If they attempt to leave before the trap is disarmed, the plate explodes
(damages the frozen character + everyone else in the room) and blocks
movement. Disarm options: thief with disarm skill, companion pulls a
lever in an adjacent room, or a "disarm traps" spell cast on the room.

Once the explosion fires (or the plate is disarmed), the victim is
unfrozen and can move freely.

Usage (build script / prototype):
    room = create_object(PressurePlateRoom, key="A narrow passage")
    room.is_trapped = True
    room.trap_damage_dice = "4d6"
    room.trap_damage_type = "fire"
    room.trap_find_dc = 20
    room.trap_disarm_dc = 18
    room.trap_description = "a pressure plate"
"""

from evennia import AttributeProperty

from typeclasses.mixins.trap import TrapMixin
from typeclasses.terrain.rooms.room_base import RoomBase


class PressurePlateRoom(TrapMixin, RoomBase):
    """
    A room with a pressure plate that freezes the first character to enter.

    MRO: TrapMixin → RoomBase → DefaultRoom
    """

    pressure_plate_victim = AttributeProperty(None)

    def at_object_creation(self):
        super().at_object_creation()
        self.at_trap_init()

    # ── Room entry — freeze victim ──

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Check pressure plate when a character enters."""
        super().at_object_receive(moved_obj, source_location, **kwargs)

        if not self.is_trapped or not self.trap_armed:
            return
        if self.pressure_plate_victim is not None:
            return  # Already has a victim
        if not hasattr(moved_obj, "take_damage"):
            return  # Not a damageable actor

        # Freeze the victim
        self.pressure_plate_victim = moved_obj
        moved_obj.msg(
            "|rYou hear a |wclick|r beneath your feet. You freeze.|n"
        )
        self.msg_contents(
            "$You() $conj(step) on something and $conj(freeze).",
            from_obj=moved_obj,
            exclude=[moved_obj],
        )

    # ── Pre-leave check — explosion if not disarmed ──

    def check_pre_leave(self, leaver, destination):
        """
        Called from FCMCharacter.at_pre_move() before movement.

        If the leaver is the frozen victim and the plate is armed,
        trigger the explosion on everyone in the room and block movement.

        Returns:
            (bool, str): (allowed, message). False blocks movement.
        """
        if (
            self.pressure_plate_victim
            and leaver == self.pressure_plate_victim
            and self.is_trapped
            and self.trap_armed
        ):
            # Explosion — damage everyone in the room
            victims = [
                obj for obj in self.contents
                if hasattr(obj, "take_damage")
            ]

            # Suppress one-shot and reset timer during AoE loop
            # (we handle state transitions manually after the loop)
            saved_one_shot = self.trap_one_shot
            saved_reset = self.trap_reset_seconds
            self.trap_one_shot = False
            self.trap_reset_seconds = 0

            for victim in victims:
                self.trigger_trap(victim, room=self)

            # Restore and handle state transitions
            self.trap_one_shot = saved_one_shot
            self.trap_reset_seconds = saved_reset
            self.trap_armed = False

            if self.trap_reset_seconds > 0:
                self._start_trap_reset_timer()

            # Unfreeze
            self.pressure_plate_victim = None

            return False, ""  # Block movement this time

        return True, None

    # ── Disarm hook — unfreeze victim ──

    def at_trap_disarm(self, character):
        """Unfreeze the victim when the trap is disarmed."""
        victim = self.pressure_plate_victim
        if victim:
            self.pressure_plate_victim = None
            victim.msg(
                "|gThe pressure plate clicks harmlessly. "
                "You can move freely.|n"
            )
            self.msg_contents(
                f"|g{victim.key} relaxes as the pressure plate is disarmed.|n",
                exclude=[victim],
            )

"""
TrapDoor — a door with a trap that triggers on open or smash.

Inherits all ExitDoor behavior (open/close/lock/smash/reciprocal pairing)
and adds TrapMixin for trap state, detection, and triggering.

Opening a trapped door always triggers the trap (whether or not detected).
Detect via search, disarm via SUBTERFUGE skill. Smashing a trapped door
triggers the trap on all room occupants before breaking the door open.

Usage (build script / prototype):
    door = create_object(TrapDoor, key="a trapped iron door",
                         location=room_a, destination=room_b)
    door.is_trapped = True
    door.trap_damage_dice = "3d6"
    door.trap_damage_type = "piercing"
    door.trap_disarm_dc = 18
    door.trap_description = "a dart trap"
"""

from typeclasses.mixins.trap import TrapMixin
from typeclasses.terrain.exits.exit_door import ExitDoor


class TrapDoor(TrapMixin, ExitDoor):
    """
    A door with a trap that triggers on open or smash.

    MRO: TrapMixin → SmashableMixin → LockableMixin → CloseableMixin
         → InvisibleObjectMixin → HiddenObjectMixin → ExitVerticalAware
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.at_trap_init()

    # ── Open triggers trap ──

    def at_open(self, opener):
        """Fire trap before reciprocal sync if armed."""
        if self.is_trapped and self.trap_armed:
            self.trigger_trap(opener)
        super().at_open(opener)

    # ── Smash triggers trap on all room occupants ──

    def at_smash_break(self):
        """Fire trap on all room occupants before breaking open."""
        if self.is_trapped and self.trap_armed:
            room = self.location
            if room:
                for obj in room.contents:
                    if hasattr(obj, "take_damage") and obj != self:
                        self.trigger_trap(obj, room)
            else:
                if self.trap_one_shot:
                    self.trap_armed = False
        super().at_smash_break()

    # ── Display ──

    def get_display_name(self, looker=None, **kwargs):
        """Append trap indicator when detected."""
        base = super().get_display_name(looker, **kwargs)
        if (
            looker
            and self.is_trap_visible_to(looker)
            and self.trap_armed
        ):
            base += " |r(trapped)|n"
        return base

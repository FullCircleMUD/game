"""
TrapChest — a chest with a trap that triggers on open or smash.

Inherits all WorldChest behavior (open/close/lock/smash/container) and
adds TrapMixin for trap state, detection, and triggering.

Opening a trapped chest always triggers the trap (whether or not detected).
Detect via search, disarm via SUBTERFUGE skill. Smashing a trapped chest
triggers the trap on all room occupants before breaking the chest open.

Usage (build script / prototype):
    chest = create_object(TrapChest, key="trapped iron chest",
                          location=room)
    chest.is_trapped = True
    chest.trap_damage_dice = "2d6"
    chest.trap_damage_type = "fire"
    chest.trap_disarm_dc = 18
    chest.trap_description = "a fire trap"
"""

from typeclasses.mixins.trap import TrapMixin
from typeclasses.world_objects.chest import WorldChest


class TrapChest(TrapMixin, WorldChest):
    """
    A chest with a trap that triggers on open or smash.

    MRO: TrapMixin → SmashableMixin → LockableMixin → CloseableMixin
         → ContainerMixin → FungibleInventoryMixin → WorldFixture
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.at_trap_init()

    # ── Open triggers trap ──

    def open(self, opener):
        """Fire trap before opening if armed."""
        if self.is_trapped and self.trap_armed:
            self.trigger_trap(opener)
        return super().open(opener)

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
                # No room context — just disarm
                if self.trap_one_shot:
                    self.trap_armed = False
        super().at_smash_break()

    # ── Display ──

    def return_appearance(self, looker, **kwargs):
        """Append trap indicator when detected."""
        base = super().return_appearance(looker, **kwargs)
        if self.is_trap_visible_to(looker) and self.trap_armed:
            base += "\n|r(You notice it is trapped!)|n"
        return base

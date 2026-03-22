"""
TripwireExit — a regular exit with a hidden tripwire trap.

Not a door — passage is always open. The tripwire is invisible until
detected via search or passive perception. Undetected tripwires trigger
on traverse; detected tripwires can be stepped over safely or disarmed
by a thief.

Usage (build script / prototype):
    exit = create_object(TripwireExit, key="north",
                         location=room_a, destination=room_b)
    exit.is_trapped = True
    exit.trap_damage_dice = "2d6"
    exit.trap_damage_type = "piercing"
    exit.trap_find_dc = 18
    exit.trap_disarm_dc = 15
    exit.trap_description = "a tripwire"
"""

from typeclasses.mixins.trap import TrapMixin
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware


class TripwireExit(TrapMixin, ExitVerticalAware):
    """
    An exit with a hidden tripwire that triggers on traverse.

    MRO: TrapMixin → ExitVerticalAware → DefaultExit
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.at_trap_init()

    # ── Traverse triggers tripwire ──

    def at_traverse(self, traversing_object, destination, **kwargs):
        """
        Check tripwire before allowing passage.

        - Armed + undetected → trigger trap, block movement
        - Armed + detected → step over safely, continue traverse
        - Disarmed → normal traverse
        """
        if self.is_trapped and self.trap_armed and not self.trap_detected:
            # Tripwire triggered — damage and block
            self.trigger_trap(traversing_object)
            traversing_object.msg(
                "You stumble and fall as you hit the tripwire!"
            )
            return  # Block movement

        if self.is_trapped and self.trap_armed and self.trap_detected:
            # Detected — step over safely
            traversing_object.msg(
                "You carefully step over the tripwire."
            )

        # Continue with height/depth/encumbrance checks
        super().at_traverse(traversing_object, destination, **kwargs)

    # ── Display ──

    def get_display_name(self, looker=None, **kwargs):
        """Show tripwire indicator when detected and armed."""
        base = super().get_display_name(looker, **kwargs)
        if (
            looker
            and self.is_trap_visible_to(looker)
            and self.trap_armed
        ):
            base += " |r(tripwire)|n"
        return base

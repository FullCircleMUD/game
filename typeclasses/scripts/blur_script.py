"""
BlurScript — per-actor script for Blur spell disadvantage application.

Combat-only: ticks once per combat round (called by combat_handler).
Each tick sets 1 round of disadvantage on every enemy against the caster.

Multi-attackers only lose accuracy on their first attack per round —
subsequent attacks that round proceed without disadvantage.

Created by Blur._execute() when the spell is cast.
Anti-stacking: each new cast removes the existing named effect + script,
then applies fresh ones.

The BLURRED state is tracked as a NamedEffect ("blurred") via
apply_named_effect() with duration_type="combat_rounds" — the named
effect system handles cleanup on combat end. This script handles
the per-tick disadvantage that the named effect system can't do natively.

Attributes (set via db before start):
    remaining_ticks (int): how many disadvantage ticks remain
"""

from evennia import DefaultScript


class BlurScript(DefaultScript):
    """
    Attached to a caster using Blur. Sets disadvantage on all enemies
    each combat round for N rounds.
    """

    def at_script_creation(self):
        self.key = "blur_effect"
        self.desc = "Blur disadvantage application"
        self.interval = -1  # no timer — combat handler calls tick_blur()
        self.persistent = True

    def tick_blur(self):
        """Called by combat handler each round."""
        from combat.combat_utils import get_sides

        char = self.obj
        if not char or not char.pk:
            self.delete()
            return

        remaining = self.db.remaining_ticks or 0
        if remaining <= 0:
            self._expire()
            return

        # Set 1 round of disadvantage on every enemy against the caster
        _, enemies = get_sides(char)
        for enemy in enemies:
            enemy_handler = enemy.scripts.get("combat_handler")
            if enemy_handler:
                enemy_handler[0].set_disadvantage(char, rounds=1)

        self.db.remaining_ticks = remaining - 1
        if self.db.remaining_ticks <= 0:
            self._expire()

    def _expire(self):
        """Remove the named effect and delete script."""
        char = self.obj
        if char and char.pk and hasattr(char, "remove_named_effect"):
            # Named effect may already be removed by clear_combat_effects
            if char.has_effect("blurred"):
                char.remove_named_effect("blurred")
        self.delete()

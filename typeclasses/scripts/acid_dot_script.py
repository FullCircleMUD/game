"""
AcidDoTScript — per-actor script for acid damage over time.

Combat-only: ticks once per combat round (called by combat_handler).
No out-of-combat ticking — acid arrow is a combat spell.

Created by AcidArrow._execute() when the spell is cast.
Anti-stacking: each new cast removes the existing named effect + script,
then applies fresh ones.

The ACID_ARROW state is tracked as a NamedEffect ("acid_arrow") via
apply_named_effect() — this script handles only the per-tick damage
that the named effect system can't do natively. On expiry, the script
removes the named effect (which handles end messaging).

Attributes (set via db before start):
    remaining_ticks (int): how many damage ticks remain
    source_name (str): name of the caster (for messages)
"""

from evennia import DefaultScript

from utils.dice_roller import dice


class AcidDoTScript(DefaultScript):
    """
    Attached to a target hit by Acid Arrow. Deals 1d4+1 acid damage
    per combat round for N rounds.
    """

    def at_script_creation(self):
        self.key = "acid_dot"
        self.desc = "Acid damage over time"
        self.interval = -1  # no timer — combat handler calls tick_acid()
        self.persistent = True

    def tick_acid(self):
        """Called by combat handler each round."""
        char = self.obj
        if not char or not char.pk:
            self.delete()
            return

        remaining = self.db.remaining_ticks or 0
        if remaining <= 0:
            self._expire()
            return

        raw_damage = dice.roll("1d4+1")
        damage = char.take_damage(raw_damage, damage_type="acid", cause="acid")

        char.msg(
            f"|GAcid continues to burn and corrode! "
            f"You take |r{damage}|G acid damage.|n"
        )
        if getattr(char, "location", None):
            char.location.msg_contents(
                f"|GAcid continues to burn and corrode {char.key}!|n",
                exclude=[char],
            )

        self.db.remaining_ticks = remaining - 1
        if self.db.remaining_ticks <= 0:
            self._expire()
            return

        # Stop ticking if target died
        if char.hp <= 0:
            self._expire()

    def _expire(self):
        """Remove the named effect (handles end messaging) and delete script."""
        char = self.obj
        if char and char.pk and hasattr(char, "remove_named_effect"):
            char.remove_named_effect("acid_arrow")
        self.delete()

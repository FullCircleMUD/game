"""
PoisonDoTScript — per-actor script for poison damage over time.

Hybrid timing: ticks per combat round when in combat (called by
combat_handler.execute_next_action), ticks every 1 second when out
of combat (script's own interval timer).

Created by BlowgunNFTItem.at_hit() when a poisoned dart hits.
Anti-stacking: each new hit removes the existing named effect + script,
then applies fresh ones.

The POISONED state is tracked as a NamedEffect ("poisoned") via
apply_named_effect() — this script handles only the per-tick damage
that the named effect system can't do natively. On expiry, the script
removes the named effect (which handles end messaging).

Attributes (set via db before start):
    remaining_ticks (int): how many damage ticks remain
    damage_dice (str): dice string rolled each tick, e.g. "1d3"
    source_name (str): name of the poisoner (for messages)
"""

from evennia import DefaultScript

from utils.dice_roller import dice


class PoisonDoTScript(DefaultScript):
    """
    Attached to a poisoned actor. Deals periodic poison damage.
    """

    def at_script_creation(self):
        self.key = "poison_dot"
        self.desc = "Poison damage over time"
        self.interval = 1  # 1-second ticks out of combat
        self.start_delay = True  # first tick after interval, not immediately
        self.persistent = True
        self.repeats = 0  # repeat until stopped

    def at_repeat(self):
        """Timer-driven tick. Skips if in combat (combat handler ticks instead)."""
        char = self.obj
        if not char or not char.pk:
            self.stop()
            return

        # In combat → combat handler calls tick_poison() directly
        if char.scripts.get("combat_handler"):
            return

        self._do_poison_tick()

    def tick_poison(self):
        """Called by combat handler each round."""
        self._do_poison_tick()

    def _do_poison_tick(self):
        """Roll poison damage, apply it, decrement counter, expire if done."""
        char = self.obj
        if not char or not char.pk:
            self.stop()
            return

        remaining = self.db.remaining_ticks or 0
        if remaining <= 0:
            self._expire()
            return

        damage_dice_str = self.db.damage_dice or "1d2"
        raw_damage = dice.roll(damage_dice_str)
        damage = char.take_damage(raw_damage, damage_type="poison", cause="poison")

        char.msg(
            f"|gPoison courses through your veins! "
            f"You take |r{damage}|g poison damage.|n"
        )
        if getattr(char, "location", None):
            char.location.msg_contents(
                f"|g{char.key} shudders as poison courses through their veins.|n",
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
            char.remove_named_effect("poisoned")
        self.delete()

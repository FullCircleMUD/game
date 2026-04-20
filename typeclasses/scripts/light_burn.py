"""
LightBurnScript — per-item script that decrements fuel on a lit light source.

Attached to any LightSourceMixin object when lit. Ticks every BURN_TICK_SECONDS,
decrements fuel_remaining, and sends warnings at low fuel levels.

When fuel reaches zero:
    - Consumable lights (torches): item is destroyed
    - Reusable lights (lanterns): item is extinguished
"""

from evennia import DefaultScript


# How often (real seconds) fuel is decremented.
BURN_TICK_SECONDS = 30


class LightBurnScript(DefaultScript):
    """
    Attached to a single light source object. Ticks down fuel.
    """

    def at_script_creation(self):
        self.key = "light_burn"
        self.desc = "Burns fuel on a lit light source"
        self.interval = BURN_TICK_SECONDS
        self.persistent = False
        self.start_delay = True  # first tick after interval
        self.repeats = 0  # repeat until stopped

    def at_repeat(self):
        obj = self.obj
        if not obj or not obj.pk:
            self.stop()
            return

        # Safety: if somehow unlit, stop
        if not getattr(obj, "is_lit", False):
            self.stop()
            return

        # Infinite fuel — nothing to do
        if obj.fuel_remaining < 0:
            self.stop()
            return

        # Decrement fuel
        obj.fuel_remaining = max(0, obj.fuel_remaining - BURN_TICK_SECONDS)

        # Warn holder/room at low fuel
        holder = self._get_holder(obj)
        if obj.fuel_remaining > 0:
            self._check_warnings(obj, holder)
        else:
            self._fuel_exhausted(obj, holder)

    def _get_holder(self, obj):
        """Return the character holding/carrying this light source, or None."""
        loc = obj.location
        if loc and hasattr(loc, "has_account"):
            return loc
        return None

    def _check_warnings(self, obj, holder):
        """Send warning messages at fuel thresholds."""
        if not holder:
            return

        remaining = obj.fuel_remaining
        max_fuel = obj.max_fuel if obj.max_fuel > 0 else 1

        pct = remaining / max_fuel
        if pct <= 0.1 and remaining + BURN_TICK_SECONDS > max_fuel * 0.1:
            holder.msg(f"|r{obj.key} is about to go out!|n")
        elif pct <= 0.25 and remaining + BURN_TICK_SECONDS > max_fuel * 0.25:
            holder.msg(f"|y{obj.key} flickers weakly...|n")

    def _fuel_exhausted(self, obj, holder):
        """Handle fuel running out."""
        if getattr(obj, "is_consumable_light", False):
            # Torch: destroy the item
            if holder:
                holder.msg(f"|r{obj.key} sputters and burns out completely.|n")
            obj.is_lit = False
            self.stop()
            obj.delete()
        else:
            # Lantern: route through extinguish() so mirror metadata captures
            # the final is_lit=False, fuel_remaining=0 snapshot consistently.
            # extinguish() internally calls _stop_burn_script() which stops us.
            obj.extinguish()
            if holder:
                holder.msg(f"|y{obj.key} runs out of fuel and goes dark.|n")

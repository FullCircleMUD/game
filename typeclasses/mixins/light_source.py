"""
LightSourceMixin — adds light-emitting behaviour to any object.

Used by torches, lanterns, world fixture lamps, and future magic items.
Objects with this mixin are detected by RoomBase.is_dark() to determine
whether a room is illuminated.

Child classes MUST:
    1. Call at_light_init() from at_object_creation()
    2. Set is_consumable_light = True if the item should be destroyed
       when fuel runs out (torches). Default is False (lanterns, fixtures).

Usage:
    class TorchNFTItem(LightSourceMixin, HoldableNFTItem):
        is_consumable_light = True

        def at_object_creation(self):
            super().at_object_creation()
            self.at_light_init()
"""

from evennia.typeclasses.attributes import AttributeProperty


class LightSourceMixin:
    """
    Mixin that gives an object the ability to emit light.

    Attributes (db):
        is_lit (bool): Whether the light source is currently lit.
        fuel_remaining (int): Seconds of fuel remaining. -1 = infinite.
        max_fuel (int): Maximum fuel capacity in seconds. -1 = infinite.

    Class-level:
        is_light_source (bool): Always True — used by room darkness checks.
        is_consumable_light (bool): If True, item is destroyed when fuel
            runs out (torches). If False, just extinguished (lanterns).
    """

    is_light_source = True
    is_consumable_light = False

    is_lit = AttributeProperty(False)
    fuel_remaining = AttributeProperty(-1)    # -1 = infinite
    max_fuel = AttributeProperty(-1)          # -1 = infinite

    def at_light_init(self):
        """
        Initialize light source state. Call from at_object_creation().
        Safe to call multiple times.
        """
        pass  # defaults set via AttributeProperty

    def light(self, lighter=None):
        """
        Light this light source.

        Args:
            lighter: The character lighting it (for messages). Can be None.

        Returns:
            (bool, str): (success, message)
        """
        if self.is_lit:
            return False, f"{self.key} is already lit."

        if self.fuel_remaining == 0:
            return False, f"{self.key} has no fuel remaining."

        self.is_lit = True
        self._start_burn_script()
        return True, f"{self.key} flickers to life."

    def extinguish(self, extinguisher=None):
        """
        Extinguish this light source, preserving remaining fuel.

        Args:
            extinguisher: The character extinguishing it. Can be None.

        Returns:
            (bool, str): (success, message)
        """
        if not self.is_lit:
            return False, f"{self.key} is not lit."

        self.is_lit = False
        self._stop_burn_script()
        return True, f"{self.key} goes dark."

    def refuel(self, amount=None):
        """
        Refuel this light source to full capacity.

        Args:
            amount: Ignored for now — always refuels to max.

        Returns:
            (bool, str): (success, message)
        """
        if self.max_fuel < 0:
            return False, f"{self.key} doesn't need fuel."

        if self.fuel_remaining >= self.max_fuel:
            return False, f"{self.key} is already full."

        self.fuel_remaining = self.max_fuel
        return True, f"{self.key} is refueled."

    def get_fuel_display(self):
        """Return a human-readable fuel string for display."""
        if self.fuel_remaining < 0:
            return ""
        minutes = self.fuel_remaining // 60
        seconds = self.fuel_remaining % 60
        return f"{minutes}:{seconds:02d}"

    # ================================================================== #
    #  Burn script management
    # ================================================================== #

    def _start_burn_script(self):
        """Attach and start a LightBurnScript if fuel is finite."""
        if self.fuel_remaining < 0:
            return  # infinite fuel — no burn script needed

        from typeclasses.scripts.light_burn import LightBurnScript

        # Don't stack scripts
        existing = self.scripts.get("light_burn")
        if existing:
            return

        self.scripts.add(LightBurnScript, autostart=True)

    def _stop_burn_script(self):
        """Stop and remove any running LightBurnScript."""
        existing = self.scripts.get("light_burn")
        if existing:
            for script in existing:
                script.stop()

"""
Light and extinguish commands for light sources (torches, lanterns).

Usage:
    light <item>       — light a held or carried light source
    extinguish <item>  — put out a lit light source

If the item is in inventory but not held, 'light' will auto-hold it
first (if the HOLD slot is free).
"""

from evennia import Command

from enums.wearslot import HumanoidWearSlot
from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem


class CmdLight(Command):
    """
    Light a torch, lantern, or other light source.

    Usage:
        light <item>

    Lights an item you are holding or carrying. If the item is in
    your inventory but not held, it will be equipped to your Hold
    slot first (if the slot is free).
    """

    key = "light"
    aliases = ("li", "lig", "ignite")
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Light what?")
            return

        query = self.args.strip()

        # Search inventory (including worn/held items)
        item = caller.search(query, location=caller)
        if not item:
            return

        # Must be a light source
        if not getattr(item, "is_light_source", False):
            caller.msg("That's not something you can light.")
            return

        # If not held, try to auto-hold it
        if item.location == caller and not self._is_held(caller, item):
            if not isinstance(item, HoldableNFTItem):
                caller.msg("You need to hold that first.")
                return
            success, msg = caller.wear(item)
            if not success:
                caller.msg(msg)
                return
            caller.msg(msg)

        # Light it
        success, msg = item.light(lighter=caller)
        if success:
            caller.msg(f"|yYou light {item.key}.|n")
            caller.location.msg_contents(
                f"$You() $conj(light) {item.key}.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg(msg)

    def _is_held(self, caller, item):
        """Check if item is in the HOLD wearslot."""
        if not hasattr(caller, "get_slot"):
            return False
        return caller.get_slot(HumanoidWearSlot.HOLD) == item


class CmdExtinguish(Command):
    """
    Extinguish a lit light source.

    Usage:
        extinguish <item>
        douse <item>
        snuff <item>

    Puts out a torch, lantern, or other light source you are
    carrying. Remaining fuel is preserved.
    """

    key = "extinguish"
    aliases = ["douse", "snuff"]
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Extinguish what?")
            return

        query = self.args.strip()

        # Search inventory
        item = caller.search(query, location=caller)
        if not item:
            return

        if not getattr(item, "is_light_source", False):
            caller.msg("That's not something you can extinguish.")
            return

        success, msg = item.extinguish(extinguisher=caller)
        if success:
            caller.msg(f"|xYou extinguish {item.key}.|n")
            caller.location.msg_contents(
                f"$You() $conj(extinguish) {item.key}.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg(msg)

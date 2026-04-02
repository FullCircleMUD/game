"""
Wield command — equip a weapon into the WIELD slot.

Usage:
    wield <weapon>
    wield #<id>
"""

from evennia import Command

from enums.wearslot import HumanoidWearSlot
from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args


class CmdWield(Command):
    """
    Wield a weapon.

    Usage:
        wield <weapon>
        wield #<id>

    Equips a weapon into your Wield slot.
    """

    key = "wield"
    aliases = ("wie", "wiel")
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Wield what?")
            return

        parsed = parse_item_args(self.args)
        if not parsed:
            caller.msg("Wield what?")
            return

        # Find the item
        if parsed.type == "token_id":
            item = self._find_by_token_id(caller, parsed.token_id)
        elif parsed.type == "item":
            item = caller.search(parsed.search_term, location=caller, exclude_worn=True)
        else:
            caller.msg("Wield what?")
            return

        if not item:
            return

        # Type check
        if not isinstance(item, WeaponMechanicsMixin):
            from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
            if isinstance(item, HoldableNFTItem):
                caller.msg(f"That's not a weapon. Try |whold {item.key}|n instead.")
            else:
                caller.msg("That's not a weapon.")
            return

        # Two-handed weapon check — can't wield 2H while holding something
        if getattr(item, "two_handed", False):
            held = caller.get_slot(HumanoidWearSlot.HOLD)
            if held:
                caller.msg(
                    f"You must remove {held.key} first"
                    f" — {item.key} requires both hands."
                )
                return

        # Attempt to wield via the mixin (wear handles slot mechanics)
        success, msg = caller.wear(item)
        if success:
            msg = f"You wield {item.key}."
        caller.msg(msg)
        if success:
            caller.location.msg_contents(
                f"$You() $conj(wield) {item.key}.",
                from_obj=caller,
                exclude=[caller],
            )

    def _find_by_token_id(self, caller, item_id):
        """Find an NFT in caller's inventory by item ID."""
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
                return obj
        caller.msg(f"You aren't carrying an item with ID #{item_id}.")
        return None

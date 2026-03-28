"""
Hold command — equip a holdable item (shield, torch, orb) or a
dual-wield weapon into the HOLD slot.

Usage:
    hold <item>
    hold #<id>
"""

from evennia import Command

from enums.wearslot import HumanoidWearSlot
from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args


class CmdHold(Command):
    """
    Hold an item.

    Usage:
        hold <item>
        hold #<id>

    Equips a shield, torch, or similar item into your Hold slot.
    Dual-wield weapons (shortswords, daggers) can also be held
    in your off-hand for extra attacks.
    """

    key = "hold"
    aliases = ("ho", "hol")
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Hold what?")
            return

        parsed = parse_item_args(self.args)
        if not parsed:
            caller.msg("Hold what?")
            return

        # Find the item
        if parsed.type == "token_id":
            item = self._find_by_token_id(caller, parsed.token_id)
        elif parsed.type == "item":
            item = caller.search(parsed.search_term, location=caller, exclude_worn=True)
        else:
            caller.msg("Hold what?")
            return

        if not item:
            return

        # Type check — holdable OR dual-wield weapon
        is_holdable = isinstance(item, HoldableNFTItem)
        is_dual_wield = (
            isinstance(item, WeaponNFTItem) and getattr(item, "can_dual_wield", False)
        )
        if not is_holdable and not is_dual_wield:
            caller.msg("That's not something you can hold.")
            return

        # Two-handed weapon check
        wielded = caller.get_slot(HumanoidWearSlot.WIELD)
        if wielded and getattr(wielded, "two_handed", False):
            caller.msg(
                f"You can't hold anything while wielding {wielded.key}"
                " — it requires both hands."
            )
            return

        # Equip — dual-wield weapons need a slot override (their wearslot is
        # WIELD, but we're putting them in HOLD)
        if is_dual_wield:
            success, msg = caller.wear(item, target_slot=HumanoidWearSlot.HOLD)
        else:
            success, msg = caller.wear(item)

        if success:
            msg = f"You hold {item.key}."
        caller.msg(msg)
        if success:
            caller.location.msg_contents(
                f"$You() $conj(hold) {item.key}.",
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

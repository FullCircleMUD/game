"""
Wear command — equip a wearable item (armor, clothing, jewelry) into a wearslot.

Usage:
    wear <item>
    wear #<id>
    wear all

For weapons use 'wield'. For shields/torches use 'hold'. `wear all`
equips every visible, unworn equippable in inventory in one pass —
including weapons and holdables.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin
from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem
from utils.item_parse import parse_item_args
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


class CmdWear(FCMCommandMixin, Command):
    """
    Equip a wearable item.

    Usage:
        wear <item>
        wear #<id>
        wear all

    Equips armor, clothing, or jewelry into the appropriate wearslot.
    For weapons use 'wield'. For shields/torches use 'hold'.

    `wear all` equips every visible, unworn equippable in your
    inventory — armour, weapons, and holdables — in one pass.
    Items that can't be equipped (slot conflict, restriction, etc.)
    are listed in a summary so you can tweak manually.
    """

    key = "wear"
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Wear what?")
            return

        parsed = parse_item_args(self.args)
        if not parsed:
            caller.msg("Wear what?")
            return

        # Darkness — can't identify items without sight
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        # Bulk: wear all equippables in one pass
        if parsed.type == "all":
            return self._wear_all(caller)

        # Find the item
        if parsed.type == "token_id":
            item = self._find_by_token_id(caller, parsed.token_id)
        elif parsed.type == "item":
            item, _ = resolve_target(
                caller, parsed.search_term, "items_inventory",
                extra_predicates=(p_can_see,),
            )
            if not item:
                # Check if already worn — specific error vs "not carrying"
                worn, _ = resolve_target(
                    caller, parsed.search_term, "items_equipped",
                    extra_predicates=(p_can_see,),
                )
                if worn:
                    caller.msg(f"You must remove {worn.key} first.")
                else:
                    caller.msg(f"You aren't carrying '{parsed.search_term}'.")
                return
        else:
            caller.msg("Wear what?")
            return

        if not item:
            return

        # Type checks — guide player to correct command
        if isinstance(item, WeaponMechanicsMixin):
            caller.msg("Use 'wield' for weapons.")
            return
        if isinstance(item, HoldableNFTItem):
            caller.msg("Use 'hold' for that.")
            return

        # Attempt to wear via the mixin
        success, msg = caller.wear(item)
        caller.msg(msg)
        if success:
            caller.location.msg_contents(
                f"$You() $conj(wear) {item.key}.",
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

    def _wear_all(self, caller):
        """Equip every visible, unworn WearableNFTItem in inventory.

        Delegates each item to caller.wear(), the universal entry point
        used by wear/wield/hold — each item's own wearslot drives slot
        selection (WIELD for weapons, HOLD for holdables, HEAD/BODY/etc.
        for armour). Errors are collected and reported per-item; the
        loop never aborts on a single failure.
        """
        worn_keys = []
        skipped = []  # list of (item.key, reason)
        attempted = False

        for obj in list(caller.contents):
            if not isinstance(obj, WearableNFTItem):
                continue
            if not p_can_see(obj, caller):
                continue
            if caller.is_worn(obj):
                continue
            attempted = True
            success, msg = caller.wear(obj)
            if success:
                worn_keys.append(obj.key)
                caller.location.msg_contents(
                    f"$You() $conj(wear) {obj.key}.",
                    from_obj=caller,
                    exclude=[caller],
                )
            else:
                skipped.append((obj.key, msg))

        if not attempted:
            caller.msg("You have nothing wearable to put on.")
            return
        if worn_keys:
            caller.msg(f"You wear: {', '.join(worn_keys)}.")
        for key, reason in skipped:
            caller.msg(f"  {key}: {reason}")

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
from utils.busy import (
    FUMBLE_BUSY_MESSAGE,
    FUMBLE_MOVE_MESSAGE,
    check_busy,
    fumble_seconds,
    start_busy,
)
from utils.item_parse import split_quantity
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_perceive
from utils.visibility import looker_is_blind


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

        split = split_quantity(self.args)
        if split is None:
            caller.msg("Wear what?")
            return
        quantity, subject = split

        # Bare "all" is the bulk action. "all helmet" is a count, and
        # only fungibles have amounts — you cannot wear a fungible.
        if subject is not None and quantity is not None:
            caller.msg(
                "You wear one piece at a time — only gold and "
                "resources come in amounts."
            )
            return

        if check_busy(caller):
            return

        # No sight check — your own pack is found by touch, and dressing
        # in the dark only takes longer. The search runs before the
        # outcome is known.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._wear(caller, subject),
                self_msg="You fumble blindly through your pack, dressing by feel...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._wear(caller, subject)

    def _wear(self, caller, subject):
        """Find the item and put it on. Success or failure both."""
        # Bulk: wear all equippables in one pass
        if subject is None:
            return self._wear_all(caller)

        # Carried items only, and never the fungible table — you cannot
        # wear gold, so "wear gold ring" is always the ring.
        if subject.startswith("#") and subject[1:].isdigit():
            item = self._find_by_token_id(caller, int(subject[1:]))
        elif subject.isdigit():
            item = self._find_by_token_id(caller, int(subject))
        else:
            matches, _ = resolve_target(
                caller, subject, "items_inventory",
                extra_predicates=(p_can_perceive,),
            )
            if not matches:
                # Already worn is a different answer to not carried.
                worn, _ = resolve_target(
                    caller, subject, "items_equipped",
                    extra_predicates=(p_can_perceive,),
                )
                worn = worn[0] if worn else None
                if worn:
                    caller.msg(f"You must remove {worn.key} first.")
                else:
                    caller.msg(f"You aren't carrying '{subject}'.")
                return
            # Identical copies are an answer; two different garments
            # sharing a word are a question Evennia already asks well.
            if len({obj.key.lower() for obj in matches}) > 1:
                caller.search(subject, candidates=matches)
                return
            item = matches[0]

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
            if not p_can_perceive(obj, caller):
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

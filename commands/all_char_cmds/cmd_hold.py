"""
Hold command — equip a holdable item (shield, torch, orb) or a
dual-wield weapon into the HOLD slot.

Usage:
    hold <item>
    hold #<id>
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.wearslot import HumanoidWearSlot
from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import split_quantity
from utils.targeting.helpers import resolve_target
from utils.busy import (
    FUMBLE_BUSY_MESSAGE,
    FUMBLE_MOVE_MESSAGE,
    check_busy,
    fumble_seconds,
    start_busy,
)
from utils.targeting.predicates import p_can_perceive
from utils.visibility import looker_is_blind


class CmdHold(FCMCommandMixin, Command):
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
    aliases = ()
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Hold what?")
            return

        if check_busy(caller):
            return

        split = split_quantity(self.args)
        if split is None or split.subject is None:
            caller.msg("Hold what?")
            return
        quantity, subject = split

        # You hold one thing — only fungibles have amounts, and you
        # cannot hold a fungible.
        if quantity is not None:
            caller.msg(
                "You hold one thing at a time — only gold and "
                "resources come in amounts."
            )
            return

        # No sight check — it is your own pack, and you know what is in it
        # by feel. Sightlessness costs time, not the action: the search
        # runs before the outcome is known, so a character who is not
        # carrying the item still spends it before hearing so.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._hold(caller, subject),
                self_msg="You fumble blindly through your pack...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._hold(caller, subject)

    def _hold(self, caller, subject):
        """Resolve the item and hold it. The outcome, success or failure."""
        # Carried items only, and never the fungible table — you cannot
        # hold gold, so "hold gold lantern" is always the lantern.
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
                caller.msg(f"You aren't carrying '{subject}'.")
                return
            # Identical copies are an answer; two different things
            # sharing a word are a question Evennia already asks well.
            if len({obj.key.lower() for obj in matches}) > 1:
                caller.search(subject, candidates=matches)
                return
            item = matches[0]

        if not item:
            return

        # Type check — holdable OR dual-wield weapon
        is_holdable = isinstance(item, HoldableNFTItem)
        is_dual_wield = (
            isinstance(item, WeaponMechanicsMixin) and getattr(item, "can_dual_wield", False)
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

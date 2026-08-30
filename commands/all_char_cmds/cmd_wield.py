"""
Wield command — equip a weapon into the WIELD slot.

Usage:
    wield <weapon>
    wield #<id>
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.wearslot import HumanoidWearSlot
from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import split_quantity
from utils.targeting.helpers import resolve_target


class CmdWield(FCMCommandMixin, Command):
    """
    Wield a weapon.

    Usage:
        wield <weapon>
        wield #<id>

    Equips a weapon into your Wield slot.
    """

    key = "wield"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Wield what?")
            return

        split = split_quantity(self.args)
        if split is None or split.subject is None:
            caller.msg("Wield what?")
            return
        quantity, subject = split

        # A weapon is not a commodity — you wield one, or none.
        # Plain Command, so no NumberedTargetCommand.parse to work
        # around: the split sees the whole argument.
        if quantity is not None:
            caller.msg(
                "You wield one weapon at a time — only gold and "
                "resources come in amounts."
            )
            return

        # Find the item
        if subject.startswith("#") and subject[1:].isdigit():
            item = self._find_by_token_id(caller, int(subject[1:]))
        elif subject.isdigit():
            item = self._find_by_token_id(caller, int(subject))
        else:
            item = self._find_carried(caller, subject)

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

    def _find_carried(self, caller, subject):
        """Resolve a carried weapon by name, or say why there isn't one.

        Worn and wielded gear is excluded at candidate selection by
        ``items_inventory``, so an equipped weapon can neither be
        re-wielded nor hide a carried one sharing its name.
        """
        matches, _ = resolve_target(caller, subject, "items_inventory")

        if not matches:
            worn, _ = resolve_target(caller, subject, "items_equipped")
            worn = worn[0] if worn else None
            if worn:
                caller.msg(f"You are already using {worn.key}.")
            else:
                caller.msg(f"You aren't carrying '{subject}'.")
            return None

        # Identical copies are an answer; two different weapons sharing
        # a word are a question Evennia already knows how to ask.
        if len({obj.key.lower() for obj in matches}) > 1:
            caller.search(subject, candidates=matches)
            return None

        return matches[0]

    def _find_by_token_id(self, caller, item_id):
        """Find an NFT in caller's inventory by item ID."""
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
                return obj
        caller.msg(f"You aren't carrying an item with ID #{item_id}.")
        return None

"""
Remove command — unequip an item from any wearslot.

Usage:
    remove <item>
    remove #<id>

Works for wearables, weapons, and holdables.
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.items.base_nft_item import BaseNFTItem
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


class CmdRemove(FCMCommandMixin, Command):
    """
    Remove an equipped item.

    Usage:
        remove <item>
        remove #<id>

    Unequips an item from any wearslot back to your inventory.
    """

    key = "remove"
    aliases = ["rem"]
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Remove what?")
            return

        split = split_quantity(self.args)
        if split is None or split.subject is None:
            caller.msg("Remove what?")
            return
        quantity, subject = split

        # Gear comes off one piece at a time — only fungibles have
        # amounts, and you cannot wear a fungible.
        if quantity is not None:
            caller.msg(
                "You remove one piece at a time — only gold and "
                "resources come in amounts."
            )
            return

        if check_busy(caller):
            return

        # No sight check — it is your own gear and it is on your body.
        # Getting it off in the dark is fiddlier than it sounds, though,
        # so sightlessness costs the time. The search runs before the
        # outcome is known.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._remove(caller, subject),
                self_msg="You feel over your gear in the dark, working at the straps...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._remove(caller, subject)

    def _remove(self, caller, subject):
        """Find the equipped item and take it off. Success or failure both."""
        # Equipped items only, and never the fungible table — you
        # cannot wear gold, so "remove gold ring" is always the ring.
        if subject.startswith("#") and subject[1:].isdigit():
            item = self._find_by_token_id(caller, int(subject[1:]))
        elif subject.isdigit():
            item = self._find_by_token_id(caller, int(subject))
        else:
            matches, _ = resolve_target(
                caller, subject, "items_equipped",
                extra_predicates=(p_can_perceive,),
            )
            if not matches:
                caller.msg(f"You aren't wearing '{subject}'.")
                return
            # A matched pair is an answer; a gold ring beside a silver
            # one is a question Evennia already knows how to ask.
            if len({obj.key.lower() for obj in matches}) > 1:
                caller.search(subject, candidates=matches)
                return
            item = matches[0]

        if not item:
            return

        # Check if it's actually worn
        if not caller.is_worn(item):
            caller.msg("You are not wearing that.")
            return

        # Block removal of lit light sources
        if getattr(item, "is_lit", False):
            caller.msg("Extinguish it first or you'll burn yourself!")
            return

        # Attempt to remove via the mixin
        success, msg = caller.remove(item)
        caller.msg(msg)
        if success:
            caller.location.msg_contents(
                f"$You() $conj(remove) {item.key}.",
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

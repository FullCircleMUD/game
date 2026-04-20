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
from utils.item_parse import parse_item_args
from utils.targeting.helpers import resolve_target
from utils.targeting.predicates import p_can_see


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

        parsed = parse_item_args(self.args)
        if not parsed:
            caller.msg("Remove what?")
            return

        # Darkness — can't identify items without sight
        room = caller.location
        if room and hasattr(room, "is_dark") and room.is_dark(caller):
            caller.msg("It's too dark to see anything.")
            return

        # Find the item — equipped items only
        if parsed.type == "token_id":
            item = self._find_by_token_id(caller, parsed.token_id)
        elif parsed.type == "item":
            item, _ = resolve_target(
                caller, parsed.search_term, "items_equipped",
                extra_predicates=(p_can_see,),
            )
            if not item:
                caller.msg(f"You aren't wearing '{parsed.search_term}'.")
                return
        else:
            caller.msg("Remove what?")
            return

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

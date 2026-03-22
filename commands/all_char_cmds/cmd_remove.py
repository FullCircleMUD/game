"""
Remove command — unequip an item from any wearslot.

Usage:
    remove <item>
    remove #<id>

Works for wearables, weapons, and holdables.
"""

from evennia import Command

from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args


class CmdRemove(Command):
    """
    Remove an equipped item.

    Usage:
        remove <item>
        remove #<id>

    Unequips an item from any wearslot back to your inventory.
    """

    key = "remove"
    aliases = ["unequip", "rem"]
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

        # Find the item
        if parsed.type == "token_id":
            item = self._find_by_token_id(caller, parsed.token_id)
        elif parsed.type == "item":
            item = caller.search(parsed.search_term, location=caller, only_worn=True)
        else:
            caller.msg("Remove what?")
            return

        if not item:
            return

        # Check if it's actually worn
        if not caller.is_worn(item):
            caller.msg("You are not wearing that.")
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

    def _find_by_token_id(self, caller, token_id):
        """Find an NFT in caller's inventory by token ID."""
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.token_id == token_id:
                return obj
        caller.msg(f"You aren't carrying an item with token ID #{token_id}.")
        return None

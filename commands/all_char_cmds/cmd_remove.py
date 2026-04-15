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
from utils.targeting.helpers import resolve_item_in_source


class CmdRemove(FCMCommandMixin, Command):
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
            # resolve_item_in_source filters source.contents via the base
            # targeting predicates. only_worn is forwarded through
            # **kwargs to FCMCharacter.search where the worn-item
            # filtering actually happens — FCMCharacter.search also
            # emits its own "You are not wearing that." message when
            # the match exists but isn't worn. nofound_string fires
            # only when nothing matches at all (neither worn nor
            # unworn items with that name).
            item = resolve_item_in_source(
                caller, caller, parsed.search_term,
                nofound_string=f"You aren't wearing '{parsed.search_term}'.",
                only_worn=True,
            )
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

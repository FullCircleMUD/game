"""
Override of Evennia's default drop command.

Adds fungible support (gold and resources) alongside the existing
object (NFT) drop. Uses the shared parse_item_args() parser for
standardised syntax across all item commands.

Usage:
    drop <obj>                    — drop an object (NFT)
    drop <amount> <fungible>      — drop gold or a resource
    drop all <fungible>           — drop all of a fungible
    drop all                      — drop everything (with confirmation)
    drop #<id>                    — drop an NFT by token ID
"""

from django.conf import settings

from evennia.commands.default.general import NumberedTargetCommand
from evennia.utils import utils

from blockchain.xrpl.currency_cache import get_all_resource_types
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args

GOLD = settings.GOLD_DISPLAY


class CmdDrop(NumberedTargetCommand):
    """
    Drop something.

    Usage:
        drop <obj>
        drop <amount> gold
        drop <amount> <resource>
        drop all gold
        drop all <resource>
        drop all
        drop #<id>

    Drop an object, gold, or resources from your inventory.
    "drop all" requires confirmation.
    """

    key = "drop"
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Drop what?")
            return

        # ---------------------------------------------------------- #
        #  Parse args through shared parser
        # ---------------------------------------------------------- #
        parsed = parse_item_args(self.args)
        if not parsed:
            caller.msg("Drop what?")
            return

        if self.number > 0 and parsed.type in ("gold", "resource"):
            parsed = parsed._replace(amount=self.number)

        # ---------------------------------------------------------- #
        #  Dispatch
        # ---------------------------------------------------------- #
        if parsed.type == "all":
            yield from self._drop_all(caller)
        elif parsed.type == "gold":
            self._drop_fungible_gold(caller, parsed.amount)
        elif parsed.type == "resource":
            self._drop_fungible_resource(
                caller, parsed.resource_id, parsed.resource_info, parsed.amount
            )
        elif parsed.type == "token_id":
            self._drop_by_token_id(caller, parsed.token_id)
        else:  # type == "item"
            self._drop_object(caller, parsed.search_term)

    # ============================================================== #
    #  Token ID lookup
    # ============================================================== #

    def _drop_by_token_id(self, caller, token_id):
        """Drop an NFT by token ID from inventory."""
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.token_id == token_id:
                if caller.is_worn(obj):
                    self.msg(f"You must remove {obj.key} first.")
                    return
                if not obj.at_pre_drop(caller):
                    return
                if obj.move_to(caller.location, quiet=True, move_type="drop"):
                    obj.at_drop(caller)
                    obj_name = obj.get_numbered_name(1, caller, return_string=True)
                    caller.location.msg_contents(
                        f"$You() $conj(drop) {obj_name}.", from_obj=caller,
                    )
                else:
                    self.msg("That can't be dropped.")
                return
        self.msg(f"You aren't carrying an item with token ID #{token_id}.")

    # ============================================================== #
    #  Fungible drop
    # ============================================================== #

    def _drop_fungible_gold(self, caller, amount):
        """Drop gold into the current room."""
        room = caller.location
        if not hasattr(room, "get_gold"):
            self.msg("You can't drop that here.")
            return

        current = caller.get_gold()
        if current <= 0:
            self.msg("You don't have any gold.")
            return
        if amount is None:
            amount = current
        if amount <= 0:
            self.msg("Amount must be positive.")
            return
        if current < amount:
            self.msg(f"You only have {current} {GOLD['unit']} of {GOLD['name']}.")
            return

        caller.transfer_gold_to(room, amount)
        caller.location.msg_contents(
            f"$You() $conj(drop) {amount} {GOLD['unit']} of {GOLD['name']}.",
            from_obj=caller,
        )

    def _drop_fungible_resource(self, caller, resource_id, resource_info, amount):
        """Drop a resource into the current room."""
        room = caller.location
        if not hasattr(room, "get_gold"):
            self.msg("You can't drop that here.")
            return

        current = caller.get_resource(resource_id)
        if current <= 0:
            self.msg(f"You don't have any {resource_info['name']}.")
            return
        if amount is None:
            amount = current
        if amount <= 0:
            self.msg("Amount must be positive.")
            return
        if current < amount:
            self.msg(
                f"You only have {current} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
            return

        caller.transfer_resource_to(room, resource_id, amount)
        caller.location.msg_contents(
            f"$You() $conj(drop) {amount} {resource_info['unit']}"
            f" of {resource_info['name']}.",
            from_obj=caller,
        )

    # ============================================================== #
    #  "drop all" — drop everything (with Y/N confirmation)
    # ============================================================== #

    def _drop_all(self, caller):
        """Drop all objects and fungibles. Requires confirmation."""
        room = caller.location

        # Build a summary of what will be dropped
        summary_lines = []
        items = [obj for obj in caller.contents if obj != caller]
        if items:
            summary_lines.append(f"  {len(items)} item(s)")
        if hasattr(caller, "get_gold") and caller.get_gold() > 0:
            summary_lines.append(
                f"  {caller.get_gold()} {GOLD['unit']} of {GOLD['name']}"
            )
        if hasattr(caller, "get_all_resources"):
            for rid, amt in caller.get_all_resources().items():
                if amt > 0:
                    info = get_all_resource_types().get(rid)
                    if info:
                        summary_lines.append(f"  {amt} {info['unit']} of {info['name']}")

        if not summary_lines:
            self.msg("You aren't carrying anything.")
            return

        answer = yield (
            f"\n|r--- WARNING ---|n"
            f"\nYou are about to drop everything you are carrying:"
            f"\n" + "\n".join(summary_lines)
            + f"\n\n|rThis will leave your belongings on the ground.|n"
            f"\n\nAre you sure? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            self.msg("Drop cancelled.")
            return

        dropped_anything = False
        skipped_worn = []

        # --- objects ---
        for obj in list(caller.contents):
            if obj == caller:
                continue
            if caller.is_worn(obj):
                skipped_worn.append(obj.key)
                continue
            if not obj.at_pre_drop(caller):
                continue
            if obj.move_to(room, quiet=True, move_type="drop"):
                obj.at_drop(caller)
                obj_name = obj.get_numbered_name(1, caller, return_string=True)
                caller.location.msg_contents(
                    f"$You() $conj(drop) {obj_name}.", from_obj=caller,
                )
                dropped_anything = True

        # --- fungibles ---
        if hasattr(room, "get_gold") and hasattr(caller, "get_gold"):
            gold = caller.get_gold()
            if gold > 0:
                caller.transfer_gold_to(room, gold)
                caller.location.msg_contents(
                    f"$You() $conj(drop) {gold} {GOLD['unit']} of {GOLD['name']}.",
                    from_obj=caller,
                )
                dropped_anything = True

            for rid, amt in list(caller.get_all_resources().items()):
                if amt > 0:
                    info = get_all_resource_types().get(rid)
                    if not info:
                        continue
                    caller.transfer_resource_to(room, rid, amt)
                    caller.location.msg_contents(
                        f"$You() $conj(drop) {amt} {info['unit']}"
                        f" of {info['name']}.",
                        from_obj=caller,
                    )
                    dropped_anything = True

        if skipped_worn:
            self.msg(
                "Worn items skipped (remove first): "
                + ", ".join(skipped_worn)
            )
        if not dropped_anything and not skipped_worn:
            self.msg("Nothing was dropped.")

    # ============================================================== #
    #  Standard object (NFT) drop
    # ============================================================== #

    def _drop_object(self, caller, search_term):
        """Standard Evennia object drop with fuzzy matching."""
        objs = caller.search(
            search_term,
            location=caller,
            nofound_string=f"You aren't carrying {search_term}.",
            multimatch_string=f"You carry more than one {search_term}:",
            stacked=self.number,
            exclude_worn=True,
        )
        if not objs:
            return
        objs = utils.make_iter(objs)

        for obj in objs:
            if not obj.at_pre_drop(caller):
                return

        moved = []
        for obj in objs:
            if obj.move_to(caller.location, quiet=True, move_type="drop"):
                moved.append(obj)
                obj.at_drop(caller)

        if not moved:
            self.msg("That can't be dropped.")
        else:
            obj_name = moved[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.location.msg_contents(
                f"$You() $conj(drop) {obj_name}.", from_obj=caller,
            )

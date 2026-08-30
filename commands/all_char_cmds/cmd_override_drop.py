"""
Override of Evennia's default drop command.

Adds fungible support (gold and resources) alongside the existing
object (NFT) drop. Counts lead and are split off by
split_quantity(); all_inventory() then decides whether the name meant
a fungible or a thing.

Usage:
    drop <obj>                    — drop an object (NFT)
    drop <amount> <fungible>      — drop gold or a resource
    drop <amount>.<fungible>      — dot syntax (e.g. drop 5.wheat)
    drop all <fungible>           — drop all of a fungible
    drop all.<fungible>           — dot syntax (e.g. drop all.gold)
    drop all                      — drop everything (with confirmation)
    drop #<id>                    — drop an NFT by token ID
"""

from django.conf import settings

from evennia.commands.default.general import NumberedTargetCommand
from evennia.utils import utils

from commands.command import FCMCommandMixin
from blockchain.xrpl.currency_cache import get_all_resource_types
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.busy import (
    FUMBLE_BUSY_MESSAGE,
    FUMBLE_MOVE_MESSAGE,
    check_busy,
    fumble_seconds,
    start_busy,
)
from utils.item_parse import ALL, split_quantity
from utils.targeting.helpers import all_inventory, resolve_target
from utils.targeting.predicates import p_can_perceive
from utils.visibility import looker_is_blind

GOLD = settings.GOLD_DISPLAY


def _amount(quantity):
    """Turn a parsed quantity into the amount the fungible handlers want.

    They read ``None`` as "all of it", so ``ALL`` maps to ``None`` and a
    missing quantity maps to one.
    """
    if quantity is ALL:
        return None
    return 1 if quantity is None else quantity


class CmdDrop(FCMCommandMixin, NumberedTargetCommand):
    """
    Drop something.

    Usage:
        drop <obj>
        drop <amount> gold             drop 5.gold
        drop <amount> <resource>       drop 5.wheat
        drop all gold                  drop all.gold
        drop all <resource>            drop all.wheat
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

        if check_busy(caller):
            return

        # ---------------------------------------------------------- #
        #  Parse args through shared parser
        # ---------------------------------------------------------- #
        split = split_quantity(self.args)
        if split is None:
            caller.msg("Drop what?")
            return
        quantity, subject = split

        # NumberedTargetCommand.parse already lifted a leading decimal
        # into self.number and removed it from self.args, so the split
        # never sees it. Evennia doing this natively is itself an
        # argument for counts leading. The dot forms and "all" reach
        # the split untouched.
        if self.number:
            quantity = self.number

        # ---------------------------------------------------------- #
        #  Dispatch
        # ---------------------------------------------------------- #
        if subject is None:  # bare "all"
            yield from self._drop_all(caller)
            return

        if subject.startswith("#") and subject[1:].isdigit():
            self._drop_by_token_id(caller, int(subject[1:]))
            return
        if subject.isdigit():
            self._drop_by_token_id(caller, int(subject))
            return

        # Sightless: the search costs time, and the answer waits for it.
        # The whole resolution defers, fungibles included — finding coins
        # in your pack by touch is the same rummaging as finding a cap.
        if looker_is_blind(caller):
            start_busy(
                caller,
                fumble_seconds(),
                lambda: self._resolve_and_drop(caller, subject, quantity),
                self_msg="You fumble blindly through your pack...",
                busy_msg=FUMBLE_BUSY_MESSAGE,
                busy_move_msg=FUMBLE_MOVE_MESSAGE,
            )
            return

        self._resolve_and_drop(caller, subject, quantity)

    def _resolve_and_drop(self, caller, subject, quantity):
        """Work out what the name meant, then act on it."""
        kind, payload = all_inventory(caller, subject, p_can_perceive)

        if kind == "gold":
            self._drop_fungible_gold(caller, _amount(quantity))
        elif kind == "resource":
            self._drop_fungible_resource(
                caller, payload["resource_id"], payload, _amount(quantity),
            )
        elif kind == "ambiguous":
            caller.msg(
                "Did you mean "
                + " or ".join(info["name"] for info in payload)
                + "?"
            )
        elif kind == "items":
            self._drop_objects(caller, subject, payload, quantity)
        else:
            self._no_match(caller, subject)

    # ============================================================== #
    #  Token ID lookup
    # ============================================================== #

    def _drop_by_token_id(self, caller, item_id):
        """Drop an NFT by item ID from inventory."""
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
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
        self.msg(f"You aren't carrying an item with ID #{item_id}.")

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

    def _drop_objects(self, caller, subject, objs, quantity):
        """Drop the one item the player meant, or say why there isn't one."""
        if quantity is not None:
            self.msg(
                f"You can't drop {quantity} of those — only gold and "
                f"resources come in amounts."
            )
            return

        # Identical copies are an answer, not a question. Two different
        # things sharing a word are a question, and dropping either
        # without asking loses the player something they didn't name.
        if len({obj.key.lower() for obj in objs}) > 1:
            caller.search(subject, candidates=objs)
            return

        obj = objs[0]
        if not obj.at_pre_drop(caller):
            return

        if not obj.move_to(caller.location, quiet=True, move_type="drop"):
            self.msg("That can't be dropped.")
            return

        obj.at_drop(caller)
        obj_name = obj.get_numbered_name(1, caller, return_string=True)
        caller.location.msg_contents(
            f"$You() $conj(drop) {obj_name}.", from_obj=caller,
        )

    def _no_match(self, caller, subject):
        """Nothing carried answers to that name. Say the most useful thing."""
        worn, _ = resolve_target(caller, subject, "items_equipped")
        worn = worn[0] if worn else None
        if worn:
            caller.msg(f"You'll have to remove {worn.key} first.")
            return
        caller.msg(f"You aren't carrying '{subject}'.")

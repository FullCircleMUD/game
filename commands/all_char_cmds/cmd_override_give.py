"""
Override of Evennia's default give command.

Adds fungible support (gold and resources) alongside the existing
object (NFT) give. Uses the shared parse_item_args() parser for
standardised syntax across all item commands.

Usage:
    give <obj> to <target>              — give an object (NFT)
    give <amount> <fungible> to <target> — give gold or a resource
    give <amount>.<fungible> to <target> — dot syntax (e.g. give 5.gold to bob)
    give all <fungible> to <target>     — give all of a fungible
    give all.<fungible> to <target>     — dot syntax (e.g. give all.wheat to bob)
    give all to <target>                — give everything (with confirmation)
    give #<id> to <target>              — give an NFT by token ID

Also supports = instead of "to":
    give <obj> = <target>
    give 50.gold = dude
"""

from django.conf import settings

from evennia.commands.default.general import NumberedTargetCommand
from evennia.utils import utils

from commands.command import FCMCommandMixin
from blockchain.xrpl.currency_cache import get_all_resource_types
from typeclasses.actors.character import FCMCharacter
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args
from utils.weight_check import (
    check_can_carry, get_item_weight, get_gold_weight, get_resource_weight,
)

GOLD = settings.GOLD_DISPLAY


class CmdGive(FCMCommandMixin, NumberedTargetCommand):
    """
    Give something to someone.

    Usage:
        give <obj> to <target>
        give <amount> gold to <target>
        give <amount> <resource> to <target>
        give all gold to <target>
        give all <resource> to <target>
        give all to <target>
        give #<id> to <target>

    Give an object, gold, or resources to another character.
    "give all" requires confirmation.
    """

    key = "give"
    rhs_split = ("=", " to ")
    locks = "cmd:all()"
    help_category = "Items"
    arg_regex = r"\s|$"

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Usage: give <item> to <target>")
            return

        # Fallback: if no "to" or "=" splitter matched, treat the last
        # word as the target (e.g. "give sword bob").
        if not self.rhs:
            parts = self.args.rsplit(None, 1)
            if len(parts) == 2:
                self.lhs, self.rhs = parts
            else:
                caller.msg("Usage: give <item> to <target>")
                return

        # ---------------------------------------------------------- #
        #  Find and validate the target
        # ---------------------------------------------------------- #
        target = caller.search(self.rhs)
        if not target:
            return

        if not isinstance(target, FCMCharacter):
            caller.msg("You can only give things to other characters.")
            return

        if target == caller:
            caller.msg("You can't give things to yourself.")
            return

        # ---------------------------------------------------------- #
        #  Parse self.lhs through shared parser
        # ---------------------------------------------------------- #
        parsed = parse_item_args(self.lhs)
        if not parsed:
            caller.msg("Give what?")
            return

        if self.number > 0 and parsed.type in ("gold", "resource"):
            parsed = parsed._replace(amount=self.number)

        if parsed.type == "item" and parsed.amount is not None:
            self.number = parsed.amount

        # ---------------------------------------------------------- #
        #  Dispatch
        # ---------------------------------------------------------- #
        if parsed.type == "all":
            yield from self._give_all(caller, target)
        elif parsed.type == "gold":
            self._give_fungible_gold(caller, target, parsed.amount)
        elif parsed.type == "resource":
            self._give_fungible_resource(
                caller, target,
                parsed.resource_id, parsed.resource_info, parsed.amount,
            )
        elif parsed.type == "token_id":
            self._give_by_token_id(caller, target, parsed.token_id)
        else:  # type == "item"
            self._give_object(caller, target, parsed.search_term)

    # ============================================================== #
    #  Token ID lookup
    # ============================================================== #

    def _give_by_token_id(self, caller, target, item_id):
        """Give an NFT by item ID to target."""
        target_name = target.get_display_name(caller)
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
                if caller.is_worn(obj):
                    self.msg(f"You must remove {obj.key} first.")
                    return
                if not obj.at_pre_give(caller, target):
                    return
                ok, msg = check_can_carry(target, get_item_weight(obj))
                if not ok:
                    caller.msg(f"{target_name} can't carry that much.")
                    return
                if obj.move_to(target, quiet=True, move_type="give"):
                    obj.at_give(caller, target)
                    obj_name = obj.get_numbered_name(1, caller, return_string=True)
                    caller.msg(f"You give {obj_name} to {target_name}.")
                    if getattr(target, "position", "standing") != "sleeping":
                        target.msg(
                            f"{caller.get_display_name(target)} gives you {obj_name}."
                        )
                    if caller.location:
                        caller.location.msg_contents(
                            f"{caller.key} gives {obj_name} to {target.key}.",
                            exclude=[caller, target], from_obj=caller,
                        )
                else:
                    caller.msg(f"You could not give that to {target_name}.")
                return
        self.msg(f"You aren't carrying an item with ID #{item_id}.")

    # ============================================================== #
    #  Fungible give
    # ============================================================== #

    def _give_fungible_gold(self, caller, target, amount):
        """Give gold to another character."""
        target_name = target.get_display_name(caller)

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

        ok, _ = check_can_carry(target, get_gold_weight(amount))
        if not ok:
            caller.msg(f"{target_name} can't carry that much.")
            return

        caller.transfer_gold_to(target, amount)
        caller.msg(
            f"You give {amount} {GOLD['unit']} of {GOLD['name']}"
            f" to {target_name}."
        )
        if getattr(target, "position", "standing") != "sleeping":
            target.msg(
                f"{caller.get_display_name(target)} gives you"
                f" {amount} {GOLD['unit']} of {GOLD['name']}."
            )
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} gives some {GOLD['name']} to {target.key}.",
                exclude=[caller, target], from_obj=caller,
            )

    def _give_fungible_resource(self, caller, target, resource_id, resource_info, amount):
        """Give a resource to another character."""
        target_name = target.get_display_name(caller)

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

        ok, _ = check_can_carry(target, get_resource_weight(resource_id, amount))
        if not ok:
            caller.msg(f"{target_name} can't carry that much.")
            return

        caller.transfer_resource_to(target, resource_id, amount)
        caller.msg(
            f"You give {amount} {resource_info['unit']}"
            f" of {resource_info['name']} to {target_name}."
        )
        if getattr(target, "position", "standing") != "sleeping":
            target.msg(
                f"{caller.get_display_name(target)} gives you"
                f" {amount} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
        if caller.location:
            caller.location.msg_contents(
                f"{caller.key} gives some {resource_info['name']} to {target.key}.",
                exclude=[caller, target], from_obj=caller,
            )

    # ============================================================== #
    #  "give all to <target>" — give everything (with confirmation)
    # ============================================================== #

    def _give_all(self, caller, target):
        """Give all objects and fungibles to target. Requires confirmation."""
        target_name = target.get_display_name(caller)

        # Build a summary of what will be given
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
                        summary_lines.append(
                            f"  {amt} {info['unit']} of {info['name']}"
                        )

        if not summary_lines:
            self.msg("You aren't carrying anything.")
            return

        answer = yield (
            f"\n|r--- WARNING ---|n"
            f"\nYou are about to give everything to {target_name}:"
            f"\n" + "\n".join(summary_lines)
            + f"\n\n|rThis cannot be undone.|n"
            f"\n\nAre you sure? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            self.msg("Give cancelled.")
            return

        gave_anything = False
        skipped_weight = False
        skipped_worn = []
        target_sleeping = getattr(target, "position", "standing") == "sleeping"

        # --- objects ---
        for obj in list(caller.contents):
            if obj == caller:
                continue
            if caller.is_worn(obj):
                skipped_worn.append(obj.key)
                continue
            if not obj.at_pre_give(caller, target):
                continue
            ok, _ = check_can_carry(target, get_item_weight(obj))
            if not ok:
                skipped_weight = True
                continue
            if obj.move_to(target, quiet=True, move_type="give"):
                obj.at_give(caller, target)
                obj_name = obj.get_numbered_name(1, caller, return_string=True)
                caller.msg(f"You give {obj_name} to {target_name}.")
                if not target_sleeping:
                    target.msg(
                        f"{caller.get_display_name(target)} gives you {obj_name}."
                    )
                gave_anything = True

        # --- fungibles ---
        if hasattr(caller, "get_gold"):
            gold = caller.get_gold()
            if gold > 0:
                ok, _ = check_can_carry(target, get_gold_weight(gold))
                if ok:
                    caller.transfer_gold_to(target, gold)
                    caller.msg(
                        f"You give {gold} {GOLD['unit']} of {GOLD['name']}"
                        f" to {target_name}."
                    )
                    if not target_sleeping:
                        target.msg(
                            f"{caller.get_display_name(target)} gives you"
                            f" {gold} {GOLD['unit']} of {GOLD['name']}."
                        )
                    gave_anything = True
                else:
                    skipped_weight = True

            for rid, amt in list(caller.get_all_resources().items()):
                if amt > 0:
                    info = get_all_resource_types().get(rid)
                    if not info:
                        continue
                    ok, _ = check_can_carry(target, get_resource_weight(rid, amt))
                    if not ok:
                        skipped_weight = True
                        continue
                    caller.transfer_resource_to(target, rid, amt)
                    caller.msg(
                        f"You give {amt} {info['unit']}"
                        f" of {info['name']} to {target_name}."
                    )
                    if not target_sleeping:
                        target.msg(
                            f"{caller.get_display_name(target)} gives you"
                            f" {amt} {info['unit']} of {info['name']}."
                        )
                    gave_anything = True

        if gave_anything and caller.location:
            caller.location.msg_contents(
                f"{caller.key} gives some belongings to {target.key}.",
                exclude=[caller, target], from_obj=caller,
            )
        if skipped_worn:
            self.msg(
                "Worn items skipped (remove first): "
                + ", ".join(skipped_worn)
            )
        if skipped_weight:
            caller.msg(f"{target_name} couldn't carry everything.")
        if not gave_anything and not skipped_worn and not skipped_weight:
            self.msg("Nothing was given.")

    # ============================================================== #
    #  Standard object (NFT) give
    # ============================================================== #

    def _give_object(self, caller, target, search_term):
        """Standard Evennia object give with fuzzy matching."""
        to_give = caller.search(
            search_term,
            location=caller,
            nofound_string=f"You aren't carrying {search_term}.",
            multimatch_string=f"You carry more than one {search_term}:",
            stacked=self.number,
            exclude_worn=True,
        )
        if not to_give:
            return

        to_give = utils.make_iter(to_give)
        target_name = target.get_display_name(caller)

        for obj in to_give:
            if not obj.at_pre_give(caller, target):
                return
            ok, _ = check_can_carry(target, get_item_weight(obj))
            if not ok:
                caller.msg(f"{target_name} can't carry that much.")
                return

        moved = []
        for obj in to_give:
            if obj.move_to(target, quiet=True, move_type="give"):
                moved.append(obj)
                obj.at_give(caller, target)

        if not moved:
            caller.msg(f"You could not give that to {target_name}.")
        else:
            obj_name = to_give[0].get_numbered_name(len(moved), caller, return_string=True)
            caller.msg(f"You give {obj_name} to {target_name}.")
            if getattr(target, "position", "standing") != "sleeping":
                target.msg(
                    f"{caller.get_display_name(target)} gives you {obj_name}."
                )
            if caller.location:
                caller.location.msg_contents(
                    f"{caller.key} gives {obj_name} to {target.key}.",
                    exclude=[caller, target], from_obj=caller,
                )

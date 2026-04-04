"""
Loot command — take items, gold, or resources from a corpse.

Available everywhere. Owner can always loot their own corpse.
Others can loot after the 5-minute owner-only lock expires.

Usage:
    loot                     — list lootable corpses and their contents
    loot <item>              — take an NFT item from a corpse
    loot gold [amount]       — take gold from a corpse
    loot <resource> [amount] — take a resource from a corpse
    loot all                 — take everything from a corpse
"""

from django.conf import settings

from evennia import Command

from commands.command import FCMCommandMixin
from blockchain.xrpl.currency_cache import get_all_resource_types
from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.world_objects.corpse import Corpse
from utils.item_parse import parse_item_args
from utils.weight_check import (
    check_can_carry, get_item_weight, get_gold_weight, get_resource_weight,
)

GOLD = settings.GOLD_DISPLAY


class CmdLoot(FCMCommandMixin, Command):
    """
    Loot all corpses in the room.

    Usage:
        loot

    Takes everything (items, gold, resources) from every lootable
    corpse in the room. You can only loot your own corpse for the
    first 5 minutes. After that, anyone can loot it.
    """

    key = "loot"
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller
        room = caller.location

        # Find corpses in the room
        corpses = [obj for obj in room.contents if isinstance(obj, Corpse)]
        if not corpses:
            caller.msg("There are no corpses here.")
            return

        # Loot everything from every lootable corpse
        looted_anything = False
        for corpse in corpses:
            if not corpse.can_loot(caller):
                continue
            if self._loot_all(caller, corpse):
                looted_anything = True

        locked_corpses = [c for c in corpses if not c.can_loot(caller)]
        if not looted_anything and locked_corpses:
            caller.msg("The corpses here are still protected.")
        elif not looted_anything:
            caller.msg("There is nothing to loot on the corpses in the room.")
        elif locked_corpses:
            caller.msg("Some corpses are still protected and were not looted.")

    # ------------------------------------------------------------------ #
    #  List corpses
    # ------------------------------------------------------------------ #

    def _list_corpses(self, caller, corpses):
        """Show all corpses in the room and their contents."""
        for corpse in corpses:
            can_access = corpse.can_loot(caller)
            lock_status = "" if can_access else " |r(locked)|n"
            caller.msg(f"\n|w{corpse.get_display_name(caller)}|n{lock_status}")

            # NFT items
            items = [obj for obj in corpse.contents if isinstance(obj, BaseNFTItem)]
            if items:
                for item in items:
                    caller.msg(f"  {item.get_display_name(caller)}")

            # Fungibles
            gold = corpse.get_gold()
            if gold > 0:
                caller.msg(f"  {GOLD['name']}: {gold} {GOLD['unit']}")

            resources = corpse.get_all_resources()
            for rid in sorted(resources.keys()):
                amt = resources[rid]
                if amt > 0:
                    info = get_all_resource_types().get(rid)
                    if info:
                        caller.msg(f"  {info['name']}: {amt} {info['unit']}")

            if not items and gold <= 0 and not any(v > 0 for v in resources.values()):
                caller.msg("  Empty.")

    # ------------------------------------------------------------------ #
    #  Find a lootable corpse
    # ------------------------------------------------------------------ #

    def _match_corpse(self, caller, corpses, search_term):
        """Check if the search term matches a corpse in the room."""
        term = search_term.lower()
        for corpse in corpses:
            display = corpse.get_display_name(caller).lower()
            if term == "corpse" or term in display:
                if corpse.can_loot(caller):
                    return corpse
        return None

    def _find_lootable_corpse(self, caller, corpses):
        """Find the first corpse this character can loot."""
        # First, try to find the caller's own corpse
        for corpse in corpses:
            if (
                hasattr(caller, "db")
                and caller.db.character_key == corpse.owner_character_key
            ):
                return corpse

        # Then try any unlocked corpse
        for corpse in corpses:
            if corpse.can_loot(caller):
                return corpse

        # All corpses are locked
        caller.msg("You cannot loot any of the corpses here yet.")
        return None

    # ------------------------------------------------------------------ #
    #  Loot individual items
    # ------------------------------------------------------------------ #

    def _loot_item(self, caller, corpse, search_term):
        """Take an NFT item from a corpse by name."""
        if not corpse.can_loot(caller):
            caller.msg("You cannot loot this corpse yet.")
            return

        term = search_term.lower()
        item = None
        for obj in corpse.contents:
            if isinstance(obj, BaseNFTItem):
                if (
                    term in obj.key.lower()
                    or any(term in a.lower() for a in obj.aliases.all())
                ):
                    item = obj
                    break

        if not item:
            caller.msg(f"No '{search_term}' found on the corpse.")
            return

        ok, msg = check_can_carry(caller, get_item_weight(item))
        if not ok:
            caller.msg(msg)
            return

        item.move_to(caller, quiet=True, move_type="get")
        caller.msg(f"You loot {item.key} from the {corpse.get_display_name(caller)}.")
        caller.location.msg_contents(
            f"{caller.key} loots {item.key} from a corpse.",
            exclude=[caller], from_obj=caller,
        )

    def _loot_by_token_id(self, caller, corpse, item_id):
        """Take an NFT item from a corpse by item ID."""
        if not corpse.can_loot(caller):
            caller.msg("You cannot loot this corpse yet.")
            return

        item = None
        for obj in corpse.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
                item = obj
                break

        if not item:
            caller.msg(f"No item with ID #{item_id} on the corpse.")
            return

        ok, msg = check_can_carry(caller, get_item_weight(item))
        if not ok:
            caller.msg(msg)
            return

        item.move_to(caller, quiet=True, move_type="get")
        caller.msg(f"You loot {item.key} from the {corpse.get_display_name(caller)}.")
        caller.location.msg_contents(
            f"{caller.key} loots {item.key} from a corpse.",
            exclude=[caller], from_obj=caller,
        )

    # ------------------------------------------------------------------ #
    #  Loot fungibles
    # ------------------------------------------------------------------ #

    def _loot_gold(self, caller, corpse, amount):
        """Take gold from a corpse."""
        if not corpse.can_loot(caller):
            caller.msg("You cannot loot this corpse yet.")
            return

        available = corpse.get_gold()
        if available <= 0:
            caller.msg("There's no gold on the corpse.")
            return
        if amount is None:
            amount = available
        if amount <= 0:
            caller.msg("Amount must be positive.")
            return
        if available < amount:
            caller.msg(f"The corpse only has {available} {GOLD['unit']} of {GOLD['name']}.")
            return

        ok, msg = check_can_carry(caller, get_gold_weight(amount))
        if not ok:
            caller.msg(msg)
            return

        corpse.transfer_gold_to(caller, amount)
        caller.msg(
            f"You loot {amount} {GOLD['unit']} of {GOLD['name']} "
            f"from the {corpse.get_display_name(caller)}."
        )
        caller.location.msg_contents(
            f"{caller.key} loots gold from a corpse.",
            exclude=[caller], from_obj=caller,
        )

    def _loot_resource(self, caller, corpse, resource_id, resource_info, amount):
        """Take a resource from a corpse."""
        if not corpse.can_loot(caller):
            caller.msg("You cannot loot this corpse yet.")
            return

        available = corpse.get_resource(resource_id)
        if available <= 0:
            caller.msg(f"There's no {resource_info['name']} on the corpse.")
            return
        if amount is None:
            amount = available
        if amount <= 0:
            caller.msg("Amount must be positive.")
            return
        if available < amount:
            caller.msg(
                f"The corpse only has {available} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
            return

        ok, msg = check_can_carry(caller, get_resource_weight(resource_id, amount))
        if not ok:
            caller.msg(msg)
            return

        corpse.transfer_resource_to(caller, resource_id, amount)
        caller.msg(
            f"You loot {amount} {resource_info['unit']} of {resource_info['name']} "
            f"from the {corpse.get_display_name(caller)}."
        )
        caller.location.msg_contents(
            f"{caller.key} loots {resource_info['name']} from a corpse.",
            exclude=[caller], from_obj=caller,
        )

    # ------------------------------------------------------------------ #
    #  Loot all
    # ------------------------------------------------------------------ #

    def _loot_all(self, caller, corpse):
        """Take everything from a corpse."""
        if not corpse.can_loot(caller):
            caller.msg("You cannot loot this corpse yet.")
            return

        looted_items = []

        # NFT items
        for obj in list(corpse.contents):
            if isinstance(obj, BaseNFTItem):
                ok, _ = check_can_carry(caller, get_item_weight(obj))
                if not ok:
                    caller.msg(f"You can't carry {obj.key} — too heavy.")
                    continue
                obj.move_to(caller, quiet=True, move_type="get")
                caller.msg(f"You loot {obj.key}.")
                looted_items.append(obj.key)

        # Gold
        gold = corpse.get_gold()
        if gold > 0:
            ok, _ = check_can_carry(caller, get_gold_weight(gold))
            if ok:
                corpse.transfer_gold_to(caller, gold)
                caller.msg(f"You loot {gold} {GOLD['unit']} of {GOLD['name']}.")
                looted_items.append(f"{gold} {GOLD['name']}")
            else:
                caller.msg("You can't carry all the gold — too heavy.")

        # Resources
        for rid, amt in list(corpse.get_all_resources().items()):
            if amt > 0:
                info = get_all_resource_types().get(rid)
                if not info:
                    continue
                ok, _ = check_can_carry(caller, get_resource_weight(rid, amt))
                if not ok:
                    caller.msg(f"You can't carry all the {info['name']} — too heavy.")
                    continue
                corpse.transfer_resource_to(caller, rid, amt)
                caller.msg(f"You loot {amt} {info['unit']} of {info['name']}.")
                looted_items.append(f"{amt} {info['name']}")

        if looted_items:
            summary = ", ".join(looted_items)
            caller.location.msg_contents(
                f"{caller.key} loots {summary} from a corpse.",
                exclude=[caller], from_obj=caller,
            )
            return True
        return False

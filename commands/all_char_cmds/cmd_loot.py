"""
Loot command — take items, gold, or resources from a corpse.

Available everywhere. Owner can always loot their own corpse.
Others can loot after the 5-minute owner-only lock expires.

Usage:
    loot / loot all — take everything from every corpse you can reach

Selection (which corpses the character can see and reach) is separate
from the looting itself, so a targeted form only needs its matching step
added. `_match_corpse`, `_loot_item`, `_loot_gold` and `_loot_resource`
are that step and are not yet reached — the grammar for naming a corpse
versus an item is still undecided.
"""

from django.conf import settings

from evennia import Command

from commands.command import FCMCommandMixin
from blockchain.xrpl.currency_cache import get_all_resource_types
from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.world_objects.corpse import Corpse
from utils.item_parse import parse_item_args
from utils.targeting.predicates import p_can_see, p_same_height
from utils.weight_check import (
    check_can_carry, get_item_weight, get_gold_weight, get_resource_weight,
)

GOLD = settings.GOLD_DISPLAY


class CmdLoot(FCMCommandMixin, Command):
    """
    Loot the corpses around you.

    Usage:
        loot
        loot all

    Takes everything — items, gold and resources — from every corpse you
    can reach. You can only loot your own corpse for the first 5 minutes;
    after that, anyone can.

    You must be able to see a corpse to loot it, and be at the same height
    as it: a corpse on the ground cannot be looted from the air, nor one
    at depth from the surface.
    """

    key = "loot"
    locks = "cmd:all()"
    help_category = "Items"

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            caller.msg("There are no corpses here.")
            return

        reachable, out_of_reach = self._select_corpses(caller, room)

        if not reachable and not out_of_reach:
            caller.msg("There are no corpses here.")
            return

        args = (self.args or "").strip()

        # ── Targeted looting — the seam, not yet wired ──
        #
        # Selection above already does the work any targeted form needs:
        # it returns the corpses this character can see and reach. What is
        # missing is the step after — matching a name and moving part of a
        # corpse's contents. `_match_corpse`, `_loot_item`, `_loot_gold`
        # and `_loot_resource` are that step, already in this file and
        # currently unreached.
        #
        # The grammar is undecided, which is why nothing is wired: naming
        # a corpse and naming an item are both plausible readings of
        # `loot <x>`, and they are ambiguous with each other unless a
        # `from` separates them (`loot <item> from <corpse>`,
        # `loot all from <corpse>`). That is a design decision, not a
        # missing implementation, so the message below stays neutral about
        # which form will eventually exist.
        if args and args.lower() != "all":
            caller.msg(
                "Only |wloot all|n is supported for now — it takes "
                "everything you can reach."
            )
            return

        # ── loot / loot all ──
        if not reachable:
            caller.msg(self._out_of_reach_message(caller, out_of_reach))
            return

        # Loot everything from every corpse the owner-lock allows.
        looted_anything = False
        for corpse in reachable:
            if not corpse.can_loot(caller):
                continue
            if self._loot_all(caller, corpse):
                looted_anything = True

        locked_corpses = [c for c in reachable if not c.can_loot(caller)]
        if not looted_anything and locked_corpses:
            caller.msg("The corpses here are still protected.")
        elif not looted_anything:
            caller.msg("There is nothing to loot on the corpses in the room.")
        elif locked_corpses:
            caller.msg("Some corpses are still protected and were not looted.")

        if out_of_reach:
            caller.msg(self._out_of_reach_message(caller, out_of_reach))

    # ------------------------------------------------------------------ #
    #  Corpse selection — sight and reach
    # ------------------------------------------------------------------ #
    #
    # Deliberately separate from the looting itself. Selection answers
    # "which corpses can this character act on at all", and knows nothing
    # about what is then taken from them. A future `loot <item>` filters
    # the reachable list by name and reuses this unchanged, rather than
    # re-deriving sight and height rules of its own.

    def _select_corpses(self, caller, room):
        """Split the room's corpses into (reachable, out_of_reach).

        Two gates, and they fail differently on purpose:

        - **Sight** (``p_can_see``) — folds in blindness, room darkness and
          concealment. A corpse the caller cannot see is dropped from both
          lists entirely. Reporting it as out of reach would announce that
          a corpse is there, which is exactly what not seeing it should
          withhold.
        - **Height** (``p_same_height``) — a corpse on the ground is not
          lootable from the air, and one at depth is not lootable from the
          surface. This one the caller *can* see, so it is reported.

        Matches the gating every other object-handling command applies —
        get, put, give, open, close, lock, unlock, read.
        """
        height_ok = p_same_height(caller)

        reachable = []
        out_of_reach = []
        for obj in room.contents:
            if not isinstance(obj, Corpse):
                continue
            if not p_can_see(obj, caller):
                continue  # unseen — say nothing at all
            if height_ok(obj, caller):
                reachable.append(obj)
            else:
                out_of_reach.append(obj)

        return reachable, out_of_reach

    @staticmethod
    def _out_of_reach_message(caller, corpses):
        """Name the corpses the caller can see but cannot reach."""
        names = [c.get_display_name(caller) for c in corpses]
        if len(names) == 1:
            listed = names[0]
        elif len(names) == 2:
            listed = f"{names[0]} or {names[1]}"
        else:
            listed = f"{', '.join(names[:-1])} or {names[-1]}"
        return f"You cannot reach {listed} from here."

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
                corpse.owner_character_key is not None
                and caller.key == corpse.owner_character_key
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

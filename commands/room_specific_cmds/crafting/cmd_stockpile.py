"""
Stockpile command — deposit shipbuilding materials at the shipyard.

Under the hood, deposits go to the player's AccountBank. The command
is filtered to only accept resources used in bank_funded recipes for
the current room's crafting type.

Usage:
    stockpile                     — show banked shipbuilding materials
    stockpile <amount> <resource> — deposit resource from inventory
    stockpile all <resource>      — deposit all of a resource
"""

from evennia import Command

from blockchain.xrpl.currency_cache import get_resource_type, get_all_resource_types
from commands.command import FCMCommandMixin
from enums.room_crafting_type import RoomCraftingType
from world.recipes import get_recipes_for_crafting_type


def _get_whitelist(room):
    """
    Return set of resource_ids used by bank_funded recipes in this room.

    Scans all recipes matching the room's crafting_type. Only includes
    resources from recipes with bank_funded=True.
    """
    try:
        crafting_type = RoomCraftingType(room.crafting_type)
    except (ValueError, AttributeError):
        return set()

    recipes = get_recipes_for_crafting_type(crafting_type)
    resource_ids = set()
    for recipe in recipes.values():
        if recipe.get("bank_funded"):
            for rid in recipe.get("ingredients", {}):
                resource_ids.add(rid)
    return resource_ids


class CmdStockpile(FCMCommandMixin, Command):
    """
    Deposit shipbuilding materials or check your stockpile.

    Usage:
        stockpile                     — show banked materials for this workshop
        stockpile <amount> <resource> — deposit resource from inventory
        stockpile all <resource>      — deposit all of a resource

    Materials are stored in your bank account and drawn on when you
    craft. Only resources used in recipes at this workshop are accepted.
    """

    key = "stockpile"
    aliases = ["stock"]
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        room = caller.location

        if not hasattr(room, "crafting_type"):
            caller.msg("There's nowhere to stockpile materials here.")
            return

        whitelist = _get_whitelist(room)
        if not whitelist:
            caller.msg("This workshop doesn't accept stockpiled materials.")
            return

        # Get bank
        if not caller.account:
            caller.msg("You need an account to stockpile materials.")
            return

        from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
        bank = ensure_bank(caller.account)

        if not self.args.strip():
            # List mode — show banked amounts for whitelisted resources
            self._show_stockpile(caller, bank, whitelist)
            return

        # Deposit mode — parse amount and resource
        self._deposit(caller, bank, whitelist)

    def _show_stockpile(self, caller, bank, whitelist):
        """Display banked quantities for shipbuilding resources."""
        lines = []
        for rid in sorted(whitelist):
            amount = bank.get_resource(rid)
            if amount > 0:
                rt = get_resource_type(rid)
                name = rt["name"] if rt else f"Resource #{rid}"
                lines.append(f"  {name}: {amount}")

        if lines:
            caller.msg(
                f"|c--- Stockpiled Materials ---|n\n"
                + "\n".join(lines)
            )
        else:
            caller.msg("You have no materials stockpiled here.")

    def _deposit(self, caller, bank, whitelist):
        """Parse args and deposit a resource."""
        args = self.args.strip()

        # Parse "all <resource>" or "<amount> <resource>"
        parts = args.split(None, 1)
        if len(parts) < 2 and parts[0].lower() != "all":
            # Single word — try as resource name
            resource_name = parts[0]
            amount = None
        elif parts[0].lower() == "all":
            if len(parts) < 2:
                caller.msg("Stockpile all of what?")
                return
            resource_name = parts[1]
            amount = None  # means "all"
        else:
            try:
                amount = int(parts[0])
            except ValueError:
                # Treat entire string as resource name
                resource_name = args
                amount = None
            else:
                resource_name = parts[1]

        # Look up resource by name
        resource_name_lower = resource_name.lower().strip()
        all_types = get_all_resource_types()
        matched_rid = None
        for rid, info in all_types.items():
            if info["name"].lower() == resource_name_lower:
                matched_rid = rid
                break

        if matched_rid is None:
            caller.msg(f"Unknown resource: {resource_name}")
            return

        if matched_rid not in whitelist:
            rt = get_resource_type(matched_rid)
            name = rt["name"] if rt else resource_name
            caller.msg(f"{name} is not needed for any recipes at this workshop.")
            return

        # Check inventory
        carried = caller.get_resource(matched_rid)
        if carried <= 0:
            rt = get_resource_type(matched_rid)
            name = rt["name"] if rt else resource_name
            caller.msg(f"You aren't carrying any {name}.")
            return

        if amount is None:
            amount = carried
        if amount <= 0:
            caller.msg("Amount must be positive.")
            return
        if amount > carried:
            rt = get_resource_type(matched_rid)
            name = rt["name"] if rt else resource_name
            caller.msg(f"You only have {carried} {name}.")
            return

        # Transfer: character → bank
        rt = get_resource_type(matched_rid)
        name = rt["name"] if rt else resource_name
        caller.transfer_resource_to(bank, matched_rid, amount)
        caller.msg(f"You stockpile {amount} {name} at the workshop.")

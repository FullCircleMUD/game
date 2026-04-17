"""
Inventory command override — shows carried items (excluding worn),
fungibles (gold + resources), and encumbrance.

Usage:
    inventory
    inv
    i
    inventory id    — show NFT token IDs and resource IDs
"""

from collections import OrderedDict

from evennia import Command

from commands.command import FCMCommandMixin
from utils.targeting.predicates import p_visible_to


class CmdInventory(FCMCommandMixin, Command):
    """
    View your inventory.

    Usage:
        inventory
        inv / i
        inventory id  — show NFT token IDs and resource IDs

    Shows items you are carrying (excluding equipped items),
    your gold and resources, and your current encumbrance.

    Items without durability (e.g. recipe scrolls, potions) are
    stacked by name. Items with durability are listed individually
    with their condition.
    """

    key = "inventory"
    aliases = ["inv", "i"]
    locks = "cmd:all()"
    help_category = "Items"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller
        show_ids = self.args.strip().lower() == "id"
        lines = []
        item_lines = []

        # Darkness — can't identify items without sight
        room = caller.location
        is_dark = room and hasattr(room, "is_dark") and room.is_dark(caller)

        # --- Carried items (excluding worn/wielded/held) ---
        if hasattr(caller, "get_carried"):
            items = caller.get_carried()
        else:
            items = caller.contents

        if items:
            if is_dark:
                # Can feel items but not identify them
                for _obj in items:
                    item_lines.append("  Something")
            else:
                # Separate into stackable (no durability) and individual (has durability)
                stackable = OrderedDict()  # key -> [visible objects]
                individual = []
                hidden_count = 0

                for obj in items:
                    if not p_visible_to(obj, caller):
                        hidden_count += 1
                        continue
                    has_durability = getattr(obj, "max_durability", 0) > 0
                    if has_durability:
                        individual.append(obj)
                    else:
                        stackable.setdefault(obj.key, []).append(obj)

                # Render stacked items first
                for name, group in stackable.items():
                    count = len(group)
                    label = f"  {name} ({count})" if count > 1 else f"  {name}"
                    if show_ids:
                        item_ids = [
                            obj.id for obj in group
                            if getattr(obj, "token_id", None) is not None
                        ]
                        if item_ids:
                            ids_str = ", ".join(f"#{iid}" for iid in item_ids)
                            label = f"{label}  |w[{ids_str}]|n"
                    item_lines.append(label)

                # Render individual items (with durability)
                for obj in individual:
                    label = f"  {obj.key}"
                    condition = (
                        obj.get_condition_label()
                        if hasattr(obj, "get_condition_label")
                        else ""
                    )
                    if condition:
                        label = f"{label}  ({condition})"
                    if show_ids and getattr(obj, "token_id", None) is not None:
                        label = f"{label}  |w[#{obj.id}]|n"
                    item_lines.append(label)

                # Invisible/hidden items — can feel but not identify
                for _ in range(hidden_count):
                    item_lines.append("  Something")

        # --- Resources (inline with items) ---
        if hasattr(caller, "get_all_resources"):
            from blockchain.xrpl.currency_cache import get_resource_type

            resources = caller.get_all_resources()
            for res_id, amount in sorted(resources.items()):
                if amount > 0:
                    rt = get_resource_type(res_id)
                    if rt:
                        if is_dark:
                            item_lines.append("  Something")
                        else:
                            label = (
                                f"  {rt['name']} ({amount})"
                                if amount > 1
                                else f"  {rt['name']}"
                            )
                            if show_ids:
                                label = f"{label}  |w[Resource #{res_id}]|n"
                            item_lines.append(label)

        if item_lines:
            lines.append("\n|wInventory:|n\n")
            lines.append("\n".join(item_lines))
        else:
            lines.append("\n|wYou are not carrying anything.|n")

        # --- Gold ---
        if hasattr(caller, "get_gold"):
            gold = caller.get_gold()
            if gold > 0:
                if is_dark:
                    lines.append("\n|wGold:|n hard to see\n")
                else:
                    lines.append(f"\n|wGold:|n {gold}\n")

        # --- Encumbrance ---
        if hasattr(caller, "get_encumbrance_display"):
            lines.append(caller.get_encumbrance_display())

        caller.msg("\n".join(lines))

"""
Rates command — show what this processing room converts and at what cost.

Usage:
    rates
"""

from evennia import Command

from blockchain.xrpl.currency_cache import get_resource_type


def _get_resource_name(res_id):
    """Look up a resource name by ID, with fallback."""
    rt = get_resource_type(res_id)
    return rt["name"] if rt else f"Resource #{res_id}"


class CmdRates(Command):
    """
    Show this room's conversion rates and costs.

    Usage:
        rates
    """

    key = "rates"
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        room = caller.location

        recipes = room.recipes
        if not recipes:
            caller.msg("This room has no processing recipes configured.")
            return

        lines = [f"\n|c--- {room.key} Rates ---|n"]
        for recipe in recipes:
            cost = recipe.get("cost", room.process_cost)
            out_name = _get_resource_name(recipe["output"])
            output_amount = recipe["amount"]

            input_parts = []
            for res_id, res_amount in recipe["inputs"].items():
                input_parts.append(f"{res_amount} {_get_resource_name(res_id)}")
            input_desc = " + ".join(input_parts)

            lines.append(
                f"  {input_desc} + {cost} gold |w→|n {output_amount} {out_name}"
            )
        lines.append(f"|c--- End of Rates ---|n")
        caller.msg("\n".join(lines))

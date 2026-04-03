"""
Available command — show recipes craftable in this specific crafting room.

Room-specific command. Filters the character's known recipes to those matching
this room's crafting type, and shows whether the room level is sufficient.

Usage:
    available
"""

from evennia import Command

from blockchain.xrpl.currency_cache import get_resource_type
from commands.command import FCMCommandMixin
from enums.room_crafting_type import RoomCraftingType


class CmdAvailable(FCMCommandMixin, Command):
    """
    Show recipes you can craft in this workshop.

    Usage:
        available

    Filters your recipe book to recipes matching this room's type.
    Shows ingredient costs, gold costs, and whether this room is
    advanced enough to craft each recipe.
    Use 'recipes' to see your full recipe book.
    """

    key = "available"
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller
        room = caller.location

        crafting_type_str = room.crafting_type
        try:
            crafting_type = RoomCraftingType(crafting_type_str)
        except ValueError:
            caller.msg("This room isn't set up for crafting.")
            return

        known = caller.get_known_recipes(crafting_type=crafting_type)

        if not known:
            caller.msg("You don't know any recipes for this workshop.")
            return

        room_fee = room.craft_cost
        room_mastery = room.mastery_level

        lines = [f"\n|c--- Available Recipes ({room.key}) ---|n"]

        for key, recipe in sorted(known.items(), key=lambda x: x[1]["name"]):
            name = recipe["name"]
            min_mastery = recipe["min_mastery"]

            # Room level check
            if room_mastery < min_mastery.value:
                level_tag = f" |r[needs {min_mastery.name} workshop]|n"
            else:
                level_tag = ""

            # Ingredients with have/need colour coding
            ingredients = recipe.get("ingredients", {})
            parts = []
            for res_id, needed in ingredients.items():
                rt = get_resource_type(res_id)
                res_name = rt["name"] if rt else f"Resource #{res_id}"
                available = caller.get_resource(res_id)
                if available >= needed:
                    parts.append(f"|g{needed} {res_name}|n")
                else:
                    parts.append(f"|r{needed} {res_name}|n ({available})")
            ingredient_str = ", ".join(parts) if parts else "none"

            lines.append(
                f"  |w{name}|n{level_tag}"
                f"\n    Materials: {ingredient_str}"
                f"\n    Workshop fee: {room_fee} gold"
            )

        lines.append(f"|c--- End of Available Recipes ---|n")
        caller.msg("\n".join(lines))

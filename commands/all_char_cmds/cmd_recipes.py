"""
Recipes command — show all recipes known by this character.

Available everywhere. Groups recipes by skill and shows the character's
mastery level for each skill.

Usage:
    recipes
"""

from evennia import Command

from commands.command import FCMCommandMixin
from blockchain.xrpl.currency_cache import get_resource_type
from enums.mastery_level import MasteryLevel


class CmdRecipes(FCMCommandMixin, Command):
    """
    Show all recipes you have learned.

    Usage:
        recipes

    Displays your recipe book grouped by skill, with your current
    mastery level and ingredient costs for each recipe.
    In a crafting room, use 'available' to see what you can craft here.
    """

    key = "recipes"
    aliases=["re", "rec", "reci","recip"]
    locks = "cmd:all()"
    help_category = "Crafting"

    def func(self):
        caller = self.caller

        known = caller.get_known_recipes()

        if not known:
            caller.msg("Your recipe book is empty. Find recipe scrolls to learn new recipes.")
            return

        # Group recipes by skill
        by_skill = {}
        for key, recipe in known.items():
            skill = recipe["skill"]
            by_skill.setdefault(skill, []).append(recipe)

        # Get character's skill mastery levels
        mastery_levels = caller.db.general_skill_mastery_levels or {}

        lines = ["\n|c--- Recipe Book ---|n"]

        for skill in sorted(by_skill.keys(), key=lambda s: s.value):
            current_level = mastery_levels.get(skill.value, 0)
            try:
                mastery_name = MasteryLevel(current_level).name
            except ValueError:
                mastery_name = "UNKNOWN"

            lines.append(f"\n  |w{skill.value.capitalize()}|n ({mastery_name})")

            for recipe in sorted(by_skill[skill], key=lambda r: r["min_mastery"].value):
                name = recipe["name"]
                min_mastery = recipe["min_mastery"]
                crafting_type = recipe["crafting_type"]

                # Ingredient summary
                ingredients = recipe.get("ingredients", {})
                parts = []
                for res_id, needed in ingredients.items():
                    rt = get_resource_type(res_id)
                    res_name = rt["name"] if rt else f"Resource #{res_id}"
                    parts.append(f"{needed} {res_name}")
                ingredient_str = ", ".join(parts) if parts else "none"

                lines.append(
                    f"    |w{name}|n [{min_mastery.name}] "
                    f"({crafting_type.value})"
                    f"\n      {ingredient_str}"
                )

        lines.append(f"\n|c--- End of Recipe Book ---|n")
        caller.msg("\n".join(lines))

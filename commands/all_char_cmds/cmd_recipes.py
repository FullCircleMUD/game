"""
Recipes command — show all recipes known by this character.

Available everywhere. With no arguments, shows a compact summary of
recipe counts by skill and tier. With a skill argument, shows full
recipe details for that skill.

Usage:
    recipes                   — summary by skill
    recipes <skill>           — detailed list for one skill
    recipes blacksmith
    recipes enchanting
    recipes wands
"""

from collections import Counter

from evennia import Command

from commands.command import FCMCommandMixin
from blockchain.xrpl.currency_cache import get_resource_type
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills


class CmdRecipes(FCMCommandMixin, Command):
    """
    Show your recipe book.

    Usage:
        recipes              — summary of recipes by skill
        recipes <skill>      — detailed list for one skill

    Examples:
        recipes
        recipes blacksmith
        recipes enchanting
        recipes wands

    With no arguments, shows a compact summary of how many recipes
    you know per skill and tier. Specify a skill name to see full
    recipe details with ingredients. Wand recipes are listed
    separately from enchanting — use 'recipes wands' to view them.
    In a crafting room, use 'available' to see what you can craft here.
    """

    key = "recipes"
    aliases = []
    locks = "cmd:all()"
    help_category = "Crafting"
    allow_while_sleeping = True

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

        # Split wand recipes out of enchanting into their own group
        if skills.ENCHANTING in by_skill:
            enchanting_recipes = by_skill[skills.ENCHANTING]
            wand_recipes = [r for r in enchanting_recipes if r["recipe_key"].startswith("wand_")]
            non_wand = [r for r in enchanting_recipes if not r["recipe_key"].startswith("wand_")]
            if non_wand:
                by_skill[skills.ENCHANTING] = non_wand
            else:
                del by_skill[skills.ENCHANTING]
            if wand_recipes:
                by_skill["_wands"] = wand_recipes

        if self.args and self.args.strip():
            skill_arg = self.args.strip()
            if skill_arg.lower() in ("wand", "wands"):
                self._show_wands_detail(caller, by_skill.get("_wands", []))
            else:
                self._show_skill_detail(caller, by_skill, skill_arg)
        else:
            self._show_summary(caller, by_skill)

    def _show_summary(self, caller, by_skill):
        """Show compact summary: recipe counts by skill and tier."""
        general_levels = caller.db.general_skill_mastery_levels or {}
        class_levels = caller.db.class_skill_mastery_levels or {}

        lines = ["\n|c--- Recipe Book ---|n"]

        # Sort real skills (skip the "_wands" sentinel)
        real_skills = [s for s in by_skill if s != "_wands"]
        for skill in sorted(real_skills, key=lambda s: s.value):
            recipes = by_skill[skill]
            # Check general skills first, then class skills (enchanting)
            current_level = general_levels.get(skill.value, 0)
            if not current_level:
                entry = class_levels.get(skill.value, 0)
                if hasattr(entry, "get"):
                    current_level = entry.get("mastery", 0)
                else:
                    current_level = int(entry) if entry else 0
            try:
                mastery_name = MasteryLevel(current_level).name
            except ValueError:
                mastery_name = "UNKNOWN"

            # Count recipes by tier
            tier_counts = Counter(
                r["min_mastery"].name for r in recipes
            )

            skill_label = skill.value.replace("_", " ").title()
            lines.append(
                f"\n  |w{skill_label}|n ({mastery_name})"
                f" — use |wrecipes {skill.value}|n to view"
            )
            for tier in MasteryLevel:
                if tier == MasteryLevel.UNSKILLED:
                    continue
                count = tier_counts.get(tier.name, 0)
                if count > 0:
                    lines.append(f"    {tier.name:<14} {count}")

        # Wand recipes section (separate from enchanting)
        if "_wands" in by_skill:
            wand_recipes = by_skill["_wands"]
            tier_counts = Counter(
                r["min_mastery"].name for r in wand_recipes
            )
            lines.append(
                f"\n  |wWands|n"
                f" — use |wrecipes wands|n to view"
            )
            for tier in MasteryLevel:
                if tier == MasteryLevel.UNSKILLED:
                    continue
                count = tier_counts.get(tier.name, 0)
                if count > 0:
                    lines.append(f"    {tier.name:<14} {count}")

        lines.append(f"\n|c--- End of Recipe Book ---|n")
        caller.msg("\n".join(lines))

    def _show_skill_detail(self, caller, by_skill, skill_arg):
        """Show full recipe details for one skill."""
        skill_lower = skill_arg.lower().replace(" ", "_")
        matched_skill = None
        for skill in by_skill:
            if skill == "_wands":
                continue
            if skill.value == skill_lower or skill.value.startswith(skill_lower):
                matched_skill = skill
                break

        if not matched_skill:
            caller.msg(
                f"You don't have any recipes for '{skill_arg}'. "
                f"Type |wrecipes|n to see your recipe book summary."
            )
            return

        recipes = by_skill[matched_skill]
        general_levels = caller.db.general_skill_mastery_levels or {}
        class_levels = caller.db.class_skill_mastery_levels or {}
        current_level = general_levels.get(matched_skill.value, 0)
        if not current_level:
            entry = class_levels.get(matched_skill.value, 0)
            if hasattr(entry, "get"):
                current_level = entry.get("mastery", 0)
            else:
                current_level = int(entry) if entry else 0
        try:
            mastery_name = MasteryLevel(current_level).name
        except ValueError:
            mastery_name = "UNKNOWN"

        skill_label = matched_skill.value.replace("_", " ").title()
        lines = [f"\n|c--- {skill_label} Recipes ---|n"]
        lines.append(f"  Your mastery: {mastery_name}\n")

        for recipe in sorted(recipes, key=lambda r: r["min_mastery"].value):
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

            # NFT ingredient summary
            nft_ingredients = recipe.get("nft_ingredients", {})
            for proto_key, needed in nft_ingredients.items():
                display_name = proto_key.replace("_", " ").title()
                parts.append(f"{needed} {display_name}")

            ingredient_str = ", ".join(parts) if parts else "none"

            lines.append(
                f"  |w{name}|n [{min_mastery.name}] "
                f"({crafting_type.value})"
                f"\n    {ingredient_str}"
            )

        lines.append(f"\n|c--- End of {skill_label} Recipes ---|n")
        caller.msg("\n".join(lines))

    def _show_wands_detail(self, caller, wand_recipes):
        """Show full recipe details for wand recipes."""
        if not wand_recipes:
            caller.msg(
                "You don't have any wand recipes. You need a wand blank "
                "in your inventory and matching spells in your spellbook."
            )
            return

        lines = ["\n|c--- Wand Recipes ---|n"]

        for recipe in sorted(wand_recipes, key=lambda r: r["min_mastery"].value):
            name = recipe["name"]
            min_mastery = recipe["min_mastery"]
            charges = recipe.get("_wand_charges", "?")

            # Ingredient summary
            ingredients = recipe.get("ingredients", {})
            parts = []
            for res_id, needed in ingredients.items():
                rt = get_resource_type(res_id)
                res_name = rt["name"] if rt else f"Resource #{res_id}"
                parts.append(f"{needed} {res_name}")

            # NFT ingredient summary
            nft_ingredients = recipe.get("nft_ingredients", {})
            for proto_key, needed in nft_ingredients.items():
                display_name = proto_key.replace("_", " ").title()
                parts.append(f"{needed} {display_name}")

            ingredient_str = ", ".join(parts) if parts else "none"

            lines.append(
                f"  |w{name}|n [{min_mastery.name}] "
                f"({charges} charges)"
                f"\n    {ingredient_str}"
            )

        lines.append(f"\n|c--- End of Wand Recipes ---|n")
        caller.msg("\n".join(lines))

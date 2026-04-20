"""
Learn command — consume a recipe NFT to permanently learn a crafting recipe.

Usage:
    learn <item>        — learn from a recipe item in your inventory

The recipe NFT is consumed (returned to game reserve) on success.
All validation (recipe exists, skill level, already known) is handled
by RecipeBookMixin.learn_recipe().
"""

from evennia import Command

from commands.command import FCMCommandMixin
from typeclasses.items.consumables.crafting_recipe_nft_item import CraftingRecipeNFTItem


class CmdLearn(FCMCommandMixin, Command):
    """
    Learn a crafting recipe from a recipe scroll in your inventory.

    Usage:
        learn <item>

    Examples:
        learn recipe
        learn training longsword recipe

    The recipe scroll is consumed when successfully learned.
    """

    key = "learn"
    aliases = []
    locks = "cmd:all()"
    help_category = "Crafting"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not self.args:
            caller.msg("Learn from what? Usage: learn <recipe item>")
            return

        # Search inventory for CraftingRecipeNFTItem matching the args
        candidates = [
            obj for obj in caller.contents
            if isinstance(obj, CraftingRecipeNFTItem)
        ]

        if not candidates:
            caller.msg("You aren't carrying any recipe scrolls.")
            return

        item = caller.search(
            self.args.strip(),
            candidates=candidates,
            quiet=True,
        )

        if not item:
            caller.msg("You don't have a recipe by that name.")
            return

        # handle list vs single result
        if isinstance(item, list):
            if len(item) > 1:
                names = ", ".join(f"{o.key} (#{o.token_id})" for o in item)
                caller.msg(f"Which recipe? {names}")
                return
            item = item[0]

        # Confirm — consuming the NFT is irreversible
        answer = yield (
            f"\n|y--- Learn Recipe ---|n"
            f"\nYou are about to learn from: |w{item.key}|n (#{item.token_id})"
            f"\nThe recipe scroll will be consumed."
            f"\n\nProceed? Y/[N]"
        )

        if answer.lower() not in ("y", "yes"):
            caller.msg("Learning cancelled.")
            return

        # Consume — at_consume delegates to learn_recipe, then deletes on success
        success, msg = item.consume(caller)
        caller.msg(msg)

"""
CraftingRecipeNFTItem — an NFT that teaches the player a crafting recipe.

When consumed via the `learn` command, delegates to
RecipeBookMixin.learn_recipe() which handles all validation (recipe
exists, not already known, skill level sufficient). On success the
item is deleted (token returns to RESERVE).

The recipe_key attribute (set by prototype) must match a key in
world.recipes.RECIPES.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.consumables.consumable_nft_item import ConsumableNFTItem


class CraftingRecipeNFTItem(ConsumableNFTItem):
    """A consumable NFT that teaches a crafting recipe when learned."""

    recipe_key = AttributeProperty("")  # set by prototype, matches world.recipes key

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("recipe", category="consumable_type")

    def at_consume(self, consumer):
        """
        Delegate to RecipeBookMixin.learn_recipe().

        Returns:
            (bool, str) — (success, message)
        """
        if not self.recipe_key:
            return (False, "This recipe scroll is blank.")
        return consumer.learn_recipe(self.recipe_key)

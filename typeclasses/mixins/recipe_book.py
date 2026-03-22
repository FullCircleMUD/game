"""
RecipeBookMixin — persistent recipe book for characters.

Characters learn recipes by consuming CraftingRecipeNFTItem objects (Phase 3)
or via NPC trainers (deferred). Once learned, a recipe is permanently available
for crafting at the appropriate room type.

Storage:
    self.db.recipe_book = {"training_longsword": True, ...}

    Keys are recipe_key strings matching entries in world.recipes.RECIPES.
    Values are always True (dict used for O(1) lookup; set can't be
    pickled reliably by Evennia's attribute system).

Usage:
    success, msg = character.learn_recipe("training_longsword")
    if character.knows_recipe("training_longsword"):
        ...
    known = character.get_known_recipes(skill=skills.CARPENTER)
"""

from world.recipes import get_recipe, RECIPES, get_recipes_for_crafting_type, get_recipes_for_skill


class RecipeBookMixin:

    def at_recipe_book_init(self):
        """Initialize recipe book storage. Call in at_object_creation()."""
        if not self.db.recipe_book:
            self.db.recipe_book = {}

    def learn_recipe(self, recipe_key):
        """
        Add a recipe to this character's book.

        Validates:
            1. Recipe exists in RECIPES
            2. Not already known
            3. Character has the required skill at min_mastery

        Returns:
            (bool, str) — (success, message)
        """
        recipe = get_recipe(recipe_key)
        if not recipe:
            return (False, "That recipe doesn't exist.")

        if self.knows_recipe(recipe_key):
            return (False, f"You already know how to craft {recipe['name']}.")

        # Check skill mastery
        skill = recipe["skill"]
        min_mastery = recipe["min_mastery"]
        current_mastery = self.db.general_skill_mastery_levels.get(skill.value, 0)
        if current_mastery < min_mastery.value:
            return (
                False,
                f"You need at least |w{min_mastery.name}|n mastery in "
                f"|w{skill.value}|n to learn this recipe.",
            )

        if self.db.recipe_book is None:
            self.db.recipe_book = {}
        self.db.recipe_book[recipe_key] = True
        return (True, f"You learn how to craft {recipe['name']}!")

    def knows_recipe(self, recipe_key):
        """Check if this character knows a recipe."""
        if not self.db.recipe_book:
            return False
        return self.db.recipe_book.get(recipe_key, False)

    def get_known_recipes(self, skill=None, crafting_type=None):
        """
        Get known recipes, optionally filtered.

        Args:
            skill: skills enum value — filter to recipes for this skill
            crafting_type: RoomCraftingType — filter to recipes for this room type

        Returns:
            dict of {recipe_key: recipe_dict} for known recipes matching filters
        """
        if not self.db.recipe_book:
            return {}

        # Start with all recipes the character knows
        known = {
            key: get_recipe(key)
            for key in self.db.recipe_book
            if get_recipe(key) is not None
        }

        if skill is not None:
            known = {k: v for k, v in known.items() if v["skill"] == skill}

        if crafting_type is not None:
            known = {k: v for k, v in known.items() if v["crafting_type"] == crafting_type}

        return known

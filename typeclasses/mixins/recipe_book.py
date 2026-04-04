"""
RecipeBookMixin — persistent recipe book for characters.

Characters learn recipes by consuming CraftingRecipeNFTItem objects (Phase 3)
or via NPC trainers (deferred). Once learned, a recipe is permanently available
for crafting at the appropriate room type.

Enchanting is special: recipes are auto-granted based on mastery level
(no scroll required). All enchanting recipes at or below the character's
ENCHANTING mastery are available automatically.

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

from enums.skills_enum import skills
from world.recipes import get_recipe, get_recipes_for_skill


def _get_enchanting_mastery(character):
    """Read enchanting mastery from class_skill_mastery_levels.

    Enchanting is a class skill (mage-only) stored in
    db.class_skill_mastery_levels with nested format:
        {"enchanting": {"mastery": 1, "classes": ["mage"]}}
    """
    class_levels = character.db.class_skill_mastery_levels or {}
    entry = class_levels.get(skills.ENCHANTING.value, 0)
    if hasattr(entry, "get"):
        return entry.get("mastery", 0)
    return int(entry)


def _get_auto_granted_enchanting_recipes(mastery_level):
    """Return enchanting recipes auto-granted at the given mastery level.

    Enchanting recipes don't require scrolls — they unlock automatically
    when the character reaches the required mastery tier.

    Args:
        mastery_level: int — character's current ENCHANTING mastery (0-5)

    Returns:
        dict of {recipe_key: recipe_dict}
    """
    if mastery_level <= 0:
        return {}
    return {
        key: recipe
        for key, recipe in get_recipes_for_skill(skills.ENCHANTING).items()
        if recipe["min_mastery"].value <= mastery_level
    }


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
        """Check if this character knows a recipe (including auto-granted enchanting)."""
        if self.db.recipe_book and self.db.recipe_book.get(recipe_key, False):
            return True
        # Check auto-granted enchanting recipes
        recipe = get_recipe(recipe_key)
        if recipe and recipe["skill"] == skills.ENCHANTING:
            enchanting_level = _get_enchanting_mastery(self)
            if enchanting_level >= recipe["min_mastery"].value:
                return True
        return False

    def get_known_recipes(self, skill=None, crafting_type=None):
        """
        Get known recipes, optionally filtered.

        Includes auto-granted enchanting recipes based on mastery level.

        Args:
            skill: skills enum value — filter to recipes for this skill
            crafting_type: RoomCraftingType — filter to recipes for this room type

        Returns:
            dict of {recipe_key: recipe_dict} for known recipes matching filters
        """
        # Start with explicitly learned recipes
        known = {}
        if self.db.recipe_book:
            known = {
                key: get_recipe(key)
                for key in self.db.recipe_book
                if get_recipe(key) is not None
            }

        # Merge auto-granted enchanting recipes
        enchanting_level = _get_enchanting_mastery(self)
        if enchanting_level > 0:
            auto = _get_auto_granted_enchanting_recipes(enchanting_level)
            for key, recipe in auto.items():
                if key not in known:
                    known[key] = recipe

        if not known:
            return {}

        if skill is not None:
            known = {k: v for k, v in known.items() if v["skill"] == skill}

        if crafting_type is not None:
            known = {k: v for k, v in known.items() if v["crafting_type"] == crafting_type}

        return known

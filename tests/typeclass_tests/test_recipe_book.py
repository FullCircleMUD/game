"""
Tests for RecipeBookMixin — learn_recipe, knows_recipe, get_known_recipes,
and the world.recipes package (auto-collection, helpers).

Uses EvenniaTest with FCMCharacter for real Evennia objects.
"""

from evennia.utils.test_resources import EvenniaTest

from enums.mastery_level import MasteryLevel
from enums.room_crafting_type import RoomCraftingType
from enums.skills_enum import skills


# ── Recipe Package Tests ─────────────────────────────────────────────────

class TestRecipePackage(EvenniaTest):
    """Test that world.recipes auto-collects recipes and helpers work."""

    def create_script(self):
        pass

    def test_recipes_dict_populated(self):
        """RECIPES dict should contain at least the training_longsword POC."""
        from world.recipes import RECIPES
        self.assertIn("training_longsword", RECIPES)

    def test_get_recipe_found(self):
        """get_recipe should return the recipe dict for a valid key."""
        from world.recipes import get_recipe
        recipe = get_recipe("training_longsword")
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Training Longsword")

    def test_get_recipe_not_found(self):
        """get_recipe should return None for an invalid key."""
        from world.recipes import get_recipe
        self.assertIsNone(get_recipe("nonexistent_recipe"))

    def test_list_recipe_keys(self):
        """list_recipe_keys should include training_longsword."""
        from world.recipes import list_recipe_keys
        keys = list_recipe_keys()
        self.assertIn("training_longsword", keys)

    def test_get_recipes_for_skill(self):
        """get_recipes_for_skill should filter by skill enum."""
        from world.recipes import get_recipes_for_skill
        carpenter_recipes = get_recipes_for_skill(skills.CARPENTER)
        self.assertIn("training_longsword", carpenter_recipes)

        blacksmith_recipes = get_recipes_for_skill(skills.BLACKSMITH)
        self.assertNotIn("training_longsword", blacksmith_recipes)

    def test_get_recipes_for_crafting_type(self):
        """get_recipes_for_crafting_type should filter by RoomCraftingType."""
        from world.recipes import get_recipes_for_crafting_type
        woodshop_recipes = get_recipes_for_crafting_type(RoomCraftingType.WOODSHOP)
        self.assertIn("training_longsword", woodshop_recipes)

        smithy_recipes = get_recipes_for_crafting_type(RoomCraftingType.SMITHY)
        self.assertNotIn("training_longsword", smithy_recipes)

    def test_recipe_data_structure(self):
        """Recipe dict should have all required fields."""
        from world.recipes import get_recipe
        recipe = get_recipe("training_longsword")
        required_keys = [
            "recipe_key", "name", "skill", "min_mastery",
            "crafting_type", "ingredients", "output_prototype",
        ]
        for key in required_keys:
            self.assertIn(key, recipe, f"Missing required key: {key}")

    def test_training_longsword_values(self):
        """Training longsword recipe should have correct values."""
        from world.recipes import get_recipe
        recipe = get_recipe("training_longsword")
        self.assertEqual(recipe["skill"], skills.CARPENTER)
        self.assertEqual(recipe["min_mastery"], MasteryLevel.BASIC)
        self.assertEqual(recipe["crafting_type"], RoomCraftingType.WOODSHOP)
        self.assertEqual(recipe["ingredients"], {7: 3})
        self.assertEqual(recipe["output_prototype"], "training_longsword")


# ── RecipeBookMixin Tests ────────────────────────────────────────────────

class TestRecipeBookInit(EvenniaTest):
    """Test recipe book initialization on character."""

    def create_script(self):
        pass

    def test_recipe_book_initialized(self):
        """New character should have an empty recipe book dict."""
        self.assertIsNotNone(self.char1.db.recipe_book)
        self.assertEqual(len(self.char1.db.recipe_book), 0)


class TestLearnRecipe(EvenniaTest):
    """Test learning recipes via RecipeBookMixin.learn_recipe()."""

    def create_script(self):
        pass

    def _give_carpenter_skill(self, char, mastery=MasteryLevel.BASIC):
        """Give a character carpenter skill at given mastery."""
        if not char.db.general_skill_mastery_levels:
            char.db.general_skill_mastery_levels = {}
        char.db.general_skill_mastery_levels[skills.CARPENTER.value] = mastery.value

    def test_learn_valid_recipe(self):
        """Character with sufficient skill should learn a recipe."""
        self._give_carpenter_skill(self.char1)
        success, msg = self.char1.learn_recipe("training_longsword")
        self.assertTrue(success)
        self.assertIn("Training Longsword", msg)
        self.assertTrue(self.char1.knows_recipe("training_longsword"))

    def test_learn_already_known(self):
        """Learning a recipe already in the book should fail."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        success, msg = self.char1.learn_recipe("training_longsword")
        self.assertFalse(success)
        self.assertIn("already know", msg)

    def test_learn_nonexistent_recipe(self):
        """Learning a recipe that doesn't exist should fail."""
        success, msg = self.char1.learn_recipe("nonexistent_thing")
        self.assertFalse(success)
        self.assertIn("doesn't exist", msg)

    def test_learn_insufficient_skill(self):
        """Learning without the required skill mastery should fail."""
        # No carpenter skill at all
        success, msg = self.char1.learn_recipe("training_longsword")
        self.assertFalse(success)
        self.assertIn("mastery", msg)

    def test_learn_unskilled_not_enough(self):
        """UNSKILLED mastery should not meet BASIC requirement."""
        self._give_carpenter_skill(self.char1, MasteryLevel.UNSKILLED)
        success, msg = self.char1.learn_recipe("training_longsword")
        self.assertFalse(success)

    def test_learn_higher_mastery_ok(self):
        """SKILLED mastery should satisfy BASIC requirement."""
        self._give_carpenter_skill(self.char1, MasteryLevel.SKILLED)
        success, msg = self.char1.learn_recipe("training_longsword")
        self.assertTrue(success)


class TestKnowsRecipe(EvenniaTest):
    """Test RecipeBookMixin.knows_recipe()."""

    def create_script(self):
        pass

    def _give_carpenter_skill(self, char, mastery=MasteryLevel.BASIC):
        if not char.db.general_skill_mastery_levels:
            char.db.general_skill_mastery_levels = {}
        char.db.general_skill_mastery_levels[skills.CARPENTER.value] = mastery.value

    def test_knows_recipe_false_empty_book(self):
        """knows_recipe should return False for empty recipe book."""
        self.assertFalse(self.char1.knows_recipe("training_longsword"))

    def test_knows_recipe_true_after_learn(self):
        """knows_recipe should return True after learning."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        self.assertTrue(self.char1.knows_recipe("training_longsword"))

    def test_knows_recipe_false_different_key(self):
        """knows_recipe should return False for unlearned recipe."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        self.assertFalse(self.char1.knows_recipe("iron_longsword"))


class TestGetKnownRecipes(EvenniaTest):
    """Test RecipeBookMixin.get_known_recipes()."""

    def create_script(self):
        pass

    def _give_carpenter_skill(self, char, mastery=MasteryLevel.BASIC):
        if not char.db.general_skill_mastery_levels:
            char.db.general_skill_mastery_levels = {}
        char.db.general_skill_mastery_levels[skills.CARPENTER.value] = mastery.value

    def test_get_known_recipes_empty(self):
        """Empty recipe book should return empty dict."""
        known = self.char1.get_known_recipes()
        self.assertEqual(known, {})

    def test_get_known_recipes_all(self):
        """Should return all known recipes when no filter."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        known = self.char1.get_known_recipes()
        self.assertIn("training_longsword", known)

    def test_get_known_recipes_filter_skill_match(self):
        """Should return recipes matching skill filter."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        known = self.char1.get_known_recipes(skill=skills.CARPENTER)
        self.assertIn("training_longsword", known)

    def test_get_known_recipes_filter_skill_no_match(self):
        """Should exclude recipes not matching skill filter."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        known = self.char1.get_known_recipes(skill=skills.BLACKSMITH)
        self.assertNotIn("training_longsword", known)

    def test_get_known_recipes_filter_crafting_type_match(self):
        """Should return recipes matching crafting_type filter."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        known = self.char1.get_known_recipes(crafting_type=RoomCraftingType.WOODSHOP)
        self.assertIn("training_longsword", known)

    def test_get_known_recipes_filter_crafting_type_no_match(self):
        """Should exclude recipes not matching crafting_type filter."""
        self._give_carpenter_skill(self.char1)
        self.char1.learn_recipe("training_longsword")
        known = self.char1.get_known_recipes(crafting_type=RoomCraftingType.SMITHY)
        self.assertNotIn("training_longsword", known)

    def test_get_known_recipes_ignores_deleted_recipes(self):
        """If a recipe_key in the book no longer exists in RECIPES, skip it."""
        self.char1.db.recipe_book = {"deleted_recipe": True}
        known = self.char1.get_known_recipes()
        self.assertNotIn("deleted_recipe", known)

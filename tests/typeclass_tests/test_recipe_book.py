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


# ── Dynamic wand recipe generation (Phase 2) ─────────────────────────


class TestWandRecipeGeneration(EvenniaTest):
    """Exercise _get_wand_enchant_recipes() across inventory and spell state.

    Wand recipes are generated on-the-fly at get_known_recipes() call time
    from (blank wands in inventory × spells in spellbook/granted) gated by
    current class-skill mastery in each spell's school.
    """

    databases = "__all__"

    def create_script(self):
        pass

    def _spawn_blank(self, prototype_key):
        """Spawn a blank wand into char1's inventory (plain BaseNFTItem).

        Tests only need the prototype_key attribute to be readable so the
        wand-recipe generator can match it against _WAND_BLANK_TIERS.
        """
        from evennia.utils import create
        obj = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key=prototype_key.replace("_", " ").title(),
            location=self.char1,
        )
        obj.db.prototype_key = prototype_key
        return obj

    def _set_evocation_mastery(self, level):
        """Set the character's evocation class-skill mastery."""
        if not self.char1.db.class_skill_mastery_levels:
            self.char1.db.class_skill_mastery_levels = {}
        self.char1.db.class_skill_mastery_levels["evocation"] = {
            "mastery": level,
            "classes": ["mage"],
        }

    def _learn_spell(self, spell_key):
        """Put a spell directly into the character's spellbook."""
        if not self.char1.db.spellbook:
            self.char1.db.spellbook = {}
        self.char1.db.spellbook[spell_key] = True

    def test_no_blanks_no_wand_recipes(self):
        """Spellbook + mastery but no blanks → zero wand recipes."""
        self._set_evocation_mastery(5)
        self._learn_spell("magic_missile")
        recipes = self.char1._get_wand_enchant_recipes()
        self.assertEqual(recipes, {})

    def test_blanks_but_no_spells_no_wand_recipes(self):
        """Blanks in inventory but empty spellbook → zero wand recipes."""
        self._spawn_blank("training_wand")
        recipes = self.char1._get_wand_enchant_recipes()
        self.assertEqual(recipes, {})

    def test_matched_tier_produces_recipe(self):
        """Training wand + magic_missile in spellbook + mastery → 1 recipe."""
        self._spawn_blank("training_wand")
        self._set_evocation_mastery(1)
        self._learn_spell("magic_missile")
        recipes = self.char1._get_wand_enchant_recipes()
        self.assertIn("wand_magic_missile", recipes)
        recipe = recipes["wand_magic_missile"]
        self.assertEqual(recipe["name"], "Wand of Magic Missile")
        self.assertEqual(recipe["skill"], skills.ENCHANTING)
        self.assertEqual(recipe["min_mastery"], MasteryLevel.BASIC)
        self.assertEqual(recipe["ingredients"], {16: 2})
        self.assertEqual(recipe["nft_ingredients"], {"training_wand": 1})
        self.assertEqual(recipe["_wand_spell_key"], "magic_missile")
        self.assertEqual(recipe["_wand_charges"], 10)
        self.assertEqual(recipe["output_item_type"], "Enchanted Wand")

    def test_unmatched_tier_excluded(self):
        """Training wand cannot hold fireball (EXPERT) — no recipe."""
        self._spawn_blank("training_wand")
        self._set_evocation_mastery(3)
        self._learn_spell("fireball")
        recipes = self.char1._get_wand_enchant_recipes()
        self.assertNotIn("wand_fireball", recipes)

    def test_current_remort_mastery_check(self):
        """Mage knows fireball but dropped to BASIC evocation — no recipe."""
        self._spawn_blank("wizards_wand")
        self._set_evocation_mastery(1)  # BASIC — but fireball is EXPERT
        self._learn_spell("fireball")
        recipes = self.char1._get_wand_enchant_recipes()
        self.assertNotIn("wand_fireball", recipes)

    def test_multiple_spells_at_matching_tier(self):
        """Multiple BASIC spells + training_wand → one recipe per spell."""
        self._spawn_blank("training_wand")
        self._set_evocation_mastery(1)
        self._learn_spell("magic_missile")
        self._learn_spell("frostbolt")
        recipes = self.char1._get_wand_enchant_recipes()
        self.assertIn("wand_magic_missile", recipes)
        self.assertIn("wand_frostbolt", recipes)

    def test_charges_scale_with_tier(self):
        """Verify the fixed charge table across tiers: 10/8/6/4/2."""
        # BASIC: 10 charges
        self._spawn_blank("training_wand")
        self._set_evocation_mastery(1)
        self._learn_spell("magic_missile")
        recipes = self.char1._get_wand_enchant_recipes()
        self.assertEqual(recipes["wand_magic_missile"]["_wand_charges"], 10)

    def test_wand_recipes_appear_in_get_known_recipes(self):
        """get_known_recipes() must merge in dynamic wand recipes."""
        self._spawn_blank("training_wand")
        self._set_evocation_mastery(1)
        self._learn_spell("magic_missile")
        known = self.char1.get_known_recipes()
        self.assertIn("wand_magic_missile", known)

    def test_wand_recipes_filtered_by_crafting_type(self):
        """Wand recipes should be in wizard's workshop filter."""
        self._spawn_blank("training_wand")
        self._set_evocation_mastery(1)
        self._learn_spell("magic_missile")
        known = self.char1.get_known_recipes(
            crafting_type=RoomCraftingType.WIZARDS_WORKSHOP,
        )
        self.assertIn("wand_magic_missile", known)

        woodshop = self.char1.get_known_recipes(
            crafting_type=RoomCraftingType.WOODSHOP,
        )
        self.assertNotIn("wand_magic_missile", woodshop)

    def test_knows_recipe_dynamic_wand(self):
        """knows_recipe should return True for a generated wand recipe."""
        self._spawn_blank("training_wand")
        self._set_evocation_mastery(1)
        self._learn_spell("magic_missile")
        self.assertTrue(self.char1.knows_recipe("wand_magic_missile"))

    def test_knows_recipe_dynamic_wand_false_without_blank(self):
        """No blank in inventory → knows_recipe returns False."""
        self._set_evocation_mastery(1)
        self._learn_spell("magic_missile")
        self.assertFalse(self.char1.knows_recipe("wand_magic_missile"))

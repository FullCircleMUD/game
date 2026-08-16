"""
RecipeBookMixin — persistent recipe book for characters.

Characters learn recipes by consuming CraftingRecipeNFTItem objects (Phase 3)
or via NPC trainers (deferred). Once learned, a recipe is permanently available
for crafting at the appropriate room type.

Enchanting is special: recipes are granted by mastery level, not learned
from scrolls. The grant engine (world/grants.py) fills db.granted_recipes
from the character's ENCHANTING mastery — see docs/knowledge-grants.md.

Storage:
    self.db.recipe_book     = {"training_longsword": True, ...}  — learned
    self.db.granted_recipes = {"rogues_bandana": True, ...}      — granted

    Keys are recipe_key strings matching entries in world.recipes.RECIPES.
    Values are always True (dict used for O(1) lookup; set can't be
    pickled reliably by Evennia's attribute system).

    Learned recipes are permanent and survive remort. Granted recipes are
    derived from mastery, so remort clears them along with the mastery.

Usage:
    success, msg = character.learn_recipe("training_longsword")
    if character.knows_recipe("training_longsword"):
        ...
    known = character.get_known_recipes(skill=skills.CARPENTER)
"""

from enums.skills_enum import skills
from world.recipes import get_recipe


# ── Wand system constants (Phase 2) ───────────────────────────────────
# Prototype keys for the five blank wand tiers the carpenter produces,
# mapped to their MasteryLevel int value. Used by the dynamic wand
# recipe generator to match spells in the caster's spellbook against
# blanks currently in their inventory.
_WAND_BLANK_TIERS = {
    "training_wand": 1,       # BASIC
    "apprentices_wand": 2,    # SKILLED
    "wizards_wand": 3,        # EXPERT
    "masters_wand": 4,        # MASTER
    "archmages_wand": 5,      # GRANDMASTER
}

# Fixed charges-per-wand by spell tier. Lower-tier spells stretch
# further on a wand: a BASIC wand of Magic Missile has 10 charges, a
# GRANDMASTER wand of Power Word Death has only 2.
_WAND_TIER_CHARGES = {
    1: 10,  # BASIC
    2: 8,   # SKILLED
    3: 6,   # EXPERT
    4: 4,   # MASTER
    5: 2,   # GRANDMASTER
}


class RecipeBookMixin:

    def at_recipe_book_init(self):
        """Initialize recipe book storage. Call in at_object_creation()."""
        if not self.db.recipe_book:
            self.db.recipe_book = {}
        if not self.db.granted_recipes:
            self.db.granted_recipes = {}

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
        """Check if this character knows a recipe (learned, granted, or a dynamic wand recipe)."""
        if self.db.recipe_book and self.db.recipe_book.get(recipe_key, False):
            return True
        if self.db.granted_recipes and self.db.granted_recipes.get(recipe_key, False):
            return True
        # Check dynamic wand recipes (recipe_key pattern: "wand_<spell_key>")
        if recipe_key.startswith("wand_"):
            return recipe_key in self._get_wand_enchant_recipes()
        return False

    def get_known_recipes(self, skill=None, crafting_type=None):
        """
        Get known recipes, optionally filtered.

        Includes mastery-granted recipes (enchanting) and dynamic
        wand-enchant recipes generated from (blanks in inventory) ×
        (spells the character knows at matching mastery).

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

        # Merge mastery-granted recipes
        for key in (self.db.granted_recipes or {}):
            if key not in known:
                recipe = get_recipe(key)
                if recipe is not None:
                    known[key] = recipe

        # Merge dynamic wand-enchant recipes (Phase 2). Static recipes
        # above take precedence if a key ever collides.
        wand_recipes = self._get_wand_enchant_recipes()
        for key, recipe in wand_recipes.items():
            if key not in known:
                known[key] = recipe

        if not known:
            return {}

        if skill is not None:
            known = {k: v for k, v in known.items() if v["skill"] == skill}

        if crafting_type is not None:
            known = {k: v for k, v in known.items() if v["crafting_type"] == crafting_type}

        return known

    def _get_wand_enchant_recipes(self):
        """Generate dynamic wand-enchant recipes from (blanks × spellbook).

        Returns a dict of {virtual_recipe_key: recipe_dict} representing
        every enchantable wand the character can currently make. A recipe
        is generated when:

        - A blank wand of matching tier sits in the character's inventory
        - The spell is in spellbook or granted_spells
        - Current mastery in the spell's school >= spell.min_mastery
          (the "must know it in current remort" rule — if a remort has
          dropped mastery below the spell's tier, the recipe disappears)

        Recipe keys follow the pattern ``wand_<spell_key>`` so they're
        stable across inventory state.
        """
        # Fast exit — no blanks means no wand recipes
        blanks_by_tier = {}
        for obj in self.contents:
            proto = None
            if getattr(obj, "db", None) is not None:
                proto = obj.db.prototype_key
            if not proto:
                continue
            tier = _WAND_BLANK_TIERS.get(proto)
            if tier is not None:
                blanks_by_tier[tier] = proto

        if not blanks_by_tier:
            return {}

        # Collect known spell keys from permanent spellbook + granted list
        known = dict(self.db.spellbook or {})
        known.update(self.db.granted_spells or {})
        if not known:
            return {}

        # Walk each known spell, check (1) matching blank (2) current mastery
        from enums.room_crafting_type import RoomCraftingType
        from world.spells.registry import SPELL_REGISTRY

        recipes = {}
        class_levels = self.db.class_skill_mastery_levels or {}

        for spell_key in known:
            spell = SPELL_REGISTRY.get(spell_key)
            if not spell:
                continue

            tier = spell.min_mastery.value
            if tier not in blanks_by_tier:
                continue  # no blank of matching tier

            # Current-remort mastery check — must still be at the tier NOW
            school_entry = class_levels.get(spell.school_key, 0)
            if hasattr(school_entry, "get"):
                current_mastery = school_entry.get("mastery", 0)
            else:
                current_mastery = int(school_entry or 0)
            if current_mastery < tier:
                continue

            blank_proto = blanks_by_tier[tier]
            charges = _WAND_TIER_CHARGES[tier]

            recipes[f"wand_{spell_key}"] = {
                "recipe_key": f"wand_{spell_key}",
                "name": f"Wand of {spell.name}",
                "skill": skills.ENCHANTING,
                "min_mastery": spell.min_mastery,
                "crafting_type": RoomCraftingType.WIZARDS_WORKSHOP,
                "ingredients": {16: 2},              # 2 Arcane Dust
                "nft_ingredients": {blank_proto: 1}, # 1 matching blank
                # Non-standard fields read by cmd_craft's wand branch:
                "output_item_type": "Enchanted Wand",
                "_wand_spell_key": spell_key,
                "_wand_charges": charges,
            }
        return recipes

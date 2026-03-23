from world.recipes.carpentry import *       # noqa: F401,F403
from world.recipes.blacksmithing import *   # noqa: F401,F403
from world.recipes.leatherworking import *  # noqa: F401,F403
from world.recipes.tailoring import *       # noqa: F401,F403
from world.recipes.jewellery import *      # noqa: F401,F403
from world.recipes.alchemy import *        # noqa: F401,F403
from world.recipes.enchanting import *     # noqa: F401,F403
from world.recipes.shipwright import *    # noqa: F401,F403

# Auto-collect all RECIPE_ dicts into lookup
import sys as _sys

_module = _sys.modules[__name__]
RECIPES = {}
for _name in dir(_module):
    if _name.startswith("RECIPE_"):
        _obj = getattr(_module, _name)
        if isinstance(_obj, dict) and "recipe_key" in _obj:
            RECIPES[_obj["recipe_key"]] = _obj


def get_recipe(key):
    """Get a recipe by its recipe_key."""
    return RECIPES.get(key)


def get_recipes_for_crafting_type(crafting_type):
    """Get all recipes for a given RoomCraftingType."""
    return {k: v for k, v in RECIPES.items() if v["crafting_type"] == crafting_type}


def get_recipes_for_skill(skill):
    """Get all recipes for a given skill."""
    return {k: v for k, v in RECIPES.items() if v["skill"] == skill}


def list_recipe_keys():
    """List all registered recipe keys."""
    return list(RECIPES.keys())


def get_recipe_by_output_prototype(prototype_key):
    """Reverse lookup: find recipe whose output_prototype matches."""
    for recipe in RECIPES.values():
        if recipe.get("output_prototype") == prototype_key:
            return recipe
    return None


def compute_repair_cost(recipe):
    """
    Compute repair resource cost for a recipe.

    If recipe has explicit 'repair_ingredients', use that.
    Otherwise auto-compute: total_materials - 1, distributed across
    resource ingredients only (NFT ingredients excluded from cost but
    counted toward the total).

    Returns dict of {resource_id: quantity} (may be empty = free repair).
    """
    if "repair_ingredients" in recipe:
        return dict(recipe["repair_ingredients"])

    ingredients = recipe.get("ingredients", {})
    nft_ingredients = recipe.get("nft_ingredients", {})

    total_materials = sum(ingredients.values()) + sum(nft_ingredients.values())
    remaining = max(0, total_materials - 1)

    repair_cost = {}
    for res_id, qty in ingredients.items():
        take = min(qty, remaining)
        if take > 0:
            repair_cost[res_id] = take
        remaining -= take
        if remaining <= 0:
            break

    return repair_cost

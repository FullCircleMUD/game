"""
Unified spawn configuration — one dict for all spawnable item types.

Keys are (item_type, type_key) tuples:
  - ("resource", resource_id)  — raw gathering resources
  - ("gold", "gold")           — gold currency
  - ("knowledge", item_key)    — spell scrolls and recipe scrolls
  - ("rare_nft", item_key)     — rare/legendary non-craftable items (future)

Distribution is NOT configured here — it is controlled entirely by tags
and spawn_<category>_max attributes on targets (rooms, mobs, containers).
"""

# Shared defaults for resource calculator entries.
_RESOURCE_DEFAULTS = {
    "calculator": "resource",
    "target_price_low": 8,
    "target_price_high": 15,
    "default_spawn_rate": 10,
    "modifier_min": 0.25,
    "modifier_max": 2.0,
}


def _res(**overrides):
    """Return a resource config dict with defaults merged."""
    return {**_RESOURCE_DEFAULTS, **overrides}


SPAWN_CONFIG = {
    # Wheat
    ("resource", 1): _res(
        target_price_low=1, target_price_high=2,
        default_spawn_rate=20,
    ),

    # Cotton
    ("resource", 10): _res(
        target_price_low=1, target_price_high=2,
        default_spawn_rate=10,
    ),

    # Wood
    ("resource", 6): _res(
        target_price_low=1, target_price_high=2,
        default_spawn_rate=10,
    ),

    # Hide
    ("resource", 8): _res(
        target_price_low=2, target_price_high=3,
        default_spawn_rate=10,
    ),

    # Animal Fat
    ("resource", 45): _res(
        target_price_low=2, target_price_high=3,
        default_spawn_rate=10,
    ),

    # Copper Ore
    ("resource", 23): _res(
        target_price_low=2, target_price_high=3,
        default_spawn_rate=10,
    ),

    # Tin Ore
    ("resource", 25): _res(
        target_price_low=2, target_price_high=3,
        default_spawn_rate=10,
    ),

    # NOT SPAWNING IN MILLHOLM ZONE - ZEROED OUT UNTIL NEW ZONES ADDED
    # Lead Ore
    ("resource", 27): _res(
        target_price_low=4, target_price_high=5,
        default_spawn_rate=0,
    ),
    # Iron Ore
    ("resource", 4): _res(
        target_price_low=2, target_price_high=3,
        default_spawn_rate=0,
    ),
    # Coal
    ("resource", 36): _res(
        target_price_low=2, target_price_high=3,
        default_spawn_rate=0,
    ),
    # Silver Ore
    ("resource", 30): _res(
        target_price_low=15, target_price_high=30,
        default_spawn_rate=0,
    ),
    # Ruby
    ("resource", 33): _res(
        target_price_low=20, target_price_high=30,
        default_spawn_rate=0,
    ),
    # Emerald
    ("resource", 34): _res(
        target_price_low=30, target_price_high=50,
        default_spawn_rate=0,
    ),
    # Diamond
    ("resource", 35): _res(
        target_price_low=50, target_price_high=100,
        default_spawn_rate=0,
    ),

    # ── Gathering — alchemy ──
    # Moonpetal
    ("resource", 12): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Bloodmoss
    ("resource", 14): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Windroot
    ("resource", 15): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Arcane Dust
    ("resource", 16): _res(
        target_price_low=6, target_price_high=10,
        default_spawn_rate=6,
    ),

    # Ogre's Cap
    ("resource", 17): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Vipervine
    ("resource", 18): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Ironbark
    ("resource", 19): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Mindcap
    ("resource", 20): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Sage Leaf
    ("resource", 21): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # Siren Petal
    ("resource", 22): _res(
        target_price_low=4, target_price_high=8,
        default_spawn_rate=6,
    ),

    # ── Gold ──
    ("gold", "gold"): {
        "calculator": "gold",
        "default_spawn_rate": 50,
        "buffer": 1.15,
        "min_runway_days": 7,
    },

    # ── Knowledge NFTs ──
    # Built dynamically by populate_knowledge_config() at service startup.

    # ── Rare NFTs (future) ──
    # ("rare_nft", "UniqueWeapon.jupiters_lightning"): {
    #     "calculator": "rare_nft",
    #     ...
    # },
}


# MasteryLevel.value → tier name for the spawn system.
_MASTERY_TO_TIER = {
    1: "basic",
    2: "skilled",
    3: "expert",
    4: "master",
    5: "gm",
}

# Base drop rates per tier (units/hour at 0% saturation).
_DROP_RATE_BY_TIER = {
    "basic": 3,
    "skilled": 2,
    "expert": 1,
    "master": 1,
    "gm": 1,
}


def populate_knowledge_config(config=None):
    """Add knowledge entries to SPAWN_CONFIG from spell/recipe registries.

    Called once by SpawnService at startup. Reads the live registries so
    new spells/recipes are picked up automatically.

    Args:
        config: Dict to populate. Defaults to module-level SPAWN_CONFIG.
    """
    if config is None:
        config = SPAWN_CONFIG

    from world.spells.registry import SPELL_REGISTRY
    from world.recipes import RECIPES

    # ── Spell scrolls ──
    for spell_key, spell in SPELL_REGISTRY.items():
        mastery_val = getattr(spell, "min_mastery", None)
        if mastery_val is None:
            continue
        tier = _MASTERY_TO_TIER.get(mastery_val.value, "basic")
        type_key = f"scroll_{spell_key}"
        config[("knowledge", type_key)] = {
            "calculator": "knowledge",
            "base_drop_rate": _DROP_RATE_BY_TIER.get(tier, 1),
            "tier": tier,
            "prototype_key": f"{spell_key}_scroll",
        }

    # ── Recipe scrolls ──
    for recipe_key, recipe in RECIPES.items():
        mastery_val = recipe.get("min_mastery")
        if mastery_val is None:
            continue
        tier = _MASTERY_TO_TIER.get(mastery_val.value, "basic")
        type_key = f"recipe_{recipe_key}"
        config[("knowledge", type_key)] = {
            "calculator": "knowledge",
            "base_drop_rate": _DROP_RATE_BY_TIER.get(tier, 1),
            "tier": tier,
            "prototype_key": f"{recipe_key}_recipe",
        }

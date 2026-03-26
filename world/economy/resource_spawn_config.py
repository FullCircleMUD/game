"""
Per-resource spawn configuration for the ResourceSpawnService.

Only raw gathering resources are listed here — NOT processed resources
(flour, ingots, cloth, leather, timber) which are player-crafted.

Keys are resource_id values from the CurrencyType seed data.
All numeric values are initial guesses — tune via observation once live.
"""

# Shared defaults — override per resource where needed.
_DEFAULTS = {
    "target_price_low": 8,
    "target_price_high": 15,
    "target_supply_per_ph": 5.0,
    "default_spawn_rate": 10,
    "max_per_room": 20,
    "modifier_min": 0.25,
    "modifier_max": 2.0,
}


def _cfg(**overrides):
    """Return a config dict with defaults merged."""
    return {**_DEFAULTS, **overrides}


RESOURCE_SPAWN_CONFIG = {
    # ── Farming ──
    1: _cfg(),                                          # Wheat
    10: _cfg(),                                         # Cotton

    # ── Forestry ──
    6: _cfg(),                                          # Wood

    # ── Hunting ──
    8: _cfg(),                                          # Hide

    # ── Mining — common ores ──
    4: _cfg(),                                          # Iron Ore
    23: _cfg(),                                         # Copper Ore
    25: _cfg(),                                         # Tin Ore
    27: _cfg(),                                         # Lead Ore
    36: _cfg(),                                         # Coal

    # ── Mining — precious ──
    30: _cfg(target_price_low=15, target_price_high=30, # Silver Ore
             target_supply_per_ph=2.0, default_spawn_rate=5,
             max_per_room=10),

    # ── Mining — gems (rare) ──
    33: _cfg(target_price_low=30, target_price_high=60, # Ruby
             target_supply_per_ph=1.0, default_spawn_rate=2,
             max_per_room=5),
    34: _cfg(target_price_low=30, target_price_high=60, # Emerald
             target_supply_per_ph=1.0, default_spawn_rate=2,
             max_per_room=5),
    35: _cfg(target_price_low=50, target_price_high=100, # Diamond
             target_supply_per_ph=0.5, default_spawn_rate=1,
             max_per_room=3),

    # ── Gathering — alchemy ──
    12: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Moonpetal
    14: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Bloodmoss
    15: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Windroot (Arcane Dust)
    16: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Arcane Dust
    17: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Ogre's Cap
    18: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Vipervine
    19: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Ironbark
    20: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Mindcap
    21: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Sage Leaf
    22: _cfg(target_supply_per_ph=3.0, default_spawn_rate=6,
             max_per_room=12),                          # Siren Petal
}


# ── Mob loot spawn config ──
# Maps resource_id → config for spawning that resource onto living mobs.
#
# "mob_share" (float 0.0–1.0): fraction of the hourly spawn budget that
# goes to mobs. The remainder goes to RoomHarvesting rooms. Set to 1.0
# for resources that ONLY come from mobs (e.g. hide from wolves).
#
# Eligible mobs are discovered automatically via loot_resource_<rid> tags
# set by CombatMob.at_object_creation(). Per-mob caps come from the mob's
# loot_resources attribute — no need to list typeclasses here.
MOB_RESOURCE_SPAWN_CONFIG = {
    8: {  # Hide — spawns only on mobs, not in rooms
        "mob_share": 1.0,
    },
}

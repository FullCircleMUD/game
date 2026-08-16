"""
Spell registry — maps spell keys to singleton Spell instances.

Spells self-register via the @register_spell decorator. The registry
is populated at import time when world/spells/__init__.py imports the
school packages (evocation, divine_healing, etc.).

Usage:
    from world.spells.registry import get_spell, get_spells_for_school

    spell = get_spell("magic_missile")
    evocation_spells = get_spells_for_school("evocation")
"""

SPELL_REGISTRY = {}


def register_spell(cls):
    """
    Class decorator — instantiates the spell and registers it.

    Usage:
        @register_spell
        class MagicMissile(Spell):
            key = "magic_missile"
            ...
    """
    instance = cls()
    SPELL_REGISTRY[instance.key] = instance
    return cls


def get_spell(key):
    """Get a spell instance by its key."""
    return SPELL_REGISTRY.get(key)


def get_spells_for_school(school):
    """Get all spells for a given school/domain. Accepts enum or string."""
    from enum import Enum
    school_str = school.value if isinstance(school, Enum) else school
    return {k: v for k, v in SPELL_REGISTRY.items() if v.school_key == school_str}


def list_spell_keys():
    """List all registered spell keys."""
    return list(SPELL_REGISTRY.keys())


def find_spell(args, fuzzy=False, spells=SPELL_REGISTRY):
    """Find a spell by name, key, or alias (case insensitive)."""
    args_lower = args.lower()
    # Exact match on name, key, or alias
    for spell_key, spell_obj in spells.items():
        if spell_obj.name.lower() == args_lower:
            return spell_obj
        if spell_key.replace("_", " ") == args_lower:
            return spell_obj

    if fuzzy:    
        # Substring fallback
        for spell_key, spell_obj in spells.items():
            if args_lower in spell_obj.name.lower():
                return spell_obj
            if args_lower in spell_key.replace("_", " "):
                return spell_obj
            
    return None
"""
Quest registry.

Quests are class-based (one Python class per quest) registered via
the @register_quest decorator. Organised by category subdirectory.

Usage:
    from world.quests import get_quest, list_quests

    quest_class = get_quest("warrior_initiation")
    all_quests = list_quests()
"""

QUEST_REGISTRY = {}


def register_quest(cls):
    """Decorator to register a quest class in the global registry."""
    QUEST_REGISTRY[cls.key] = cls
    return cls


def get_quest(key):
    """Get a quest class by key, or None."""
    return QUEST_REGISTRY.get(key)


def list_quests():
    """Get all registered quest classes."""
    return list(QUEST_REGISTRY.values())


def get_quests_by_type(quest_type):
    """Get all registered quest classes of a given type."""
    return [q for q in QUEST_REGISTRY.values() if q.quest_type == quest_type]


# Auto-import quest modules to trigger @register_quest decorators.
from world.quests.guild import *  # noqa: F401, F403, E402
from world.quests.rat_cellar import *  # noqa: F401, F403, E402
from world.quests.bakers_flour import *  # noqa: F401, F403, E402
from world.quests.oakwright_timber import *  # noqa: F401, F403, E402

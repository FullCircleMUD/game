"""
Dungeon template registry.

Templates are registered at import time and looked up by template_id
when a player enters a dungeon entrance room.
"""

from world.dungeons.dungeon_template import DungeonTemplate

DUNGEON_REGISTRY: dict[str, DungeonTemplate] = {}


def register_dungeon(template: DungeonTemplate):
    """Register a dungeon template."""
    DUNGEON_REGISTRY[template.template_id] = template


def get_dungeon_template(template_id: str) -> DungeonTemplate:
    """Look up a dungeon template by ID. Raises KeyError if not found."""
    return DUNGEON_REGISTRY[template_id]

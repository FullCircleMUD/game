"""
CharacterClass — enum of all playable character classes.

Single source of truth for valid class identifiers. Values are lowercase
strings matching how classes are stored in character.db.classes.
"""

from enum import Enum


class CharacterClass(str, Enum):
    """Playable character classes."""

    WARRIOR = "warrior"
    THIEF = "thief"
    CLERIC = "cleric"
    MAGE = "mage"
    PALADIN = "paladin"
    BARBARIAN = "barbarian"
    RANGER = "ranger"
    DRUID = "druid"
    NINJA = "ninja"
    BARD = "bard"

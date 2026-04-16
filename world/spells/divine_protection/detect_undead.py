"""
Detect Undead — divine_protection variant.

Identical to the Divine Revelation version. Thin subclass so clerics
who trained Divine Protection can still sense the unholy.
"""

from enums.skills_enum import skills
from world.spells.divine_revelation.detect_undead import DetectUndead
from world.spells.registry import register_spell


@register_spell
class ProtectionDetectUndead(DetectUndead):
    key = "protection_detect_undead"
    name = "Detect Undead"
    school = skills.DIVINE_PROTECTION

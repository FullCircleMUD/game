"""
Earthquake — nature magic spell, available from GRANDMASTER mastery.

Massive unsafe AoE that hits everything in the room (including caster
and allies). Deals physical/bludgeoning damage and applies STUNNED
condition (knockdown).

Scaling:
    GM(5): massive damage + STUNNED, mana 100

Cooldown: 3 rounds (default GM).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Earthquake(Spell):
    key = "earthquake"
    aliases = ["quake", "eq"]
    name = "Earthquake"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "none"
    description = "Shakes the very earth, devastating everything in the room."
    mechanics = (
        "Unsafe AoE — hits EVERYTHING including caster and allies.\n"
        "Massive bludgeoning damage + STUNNED/knockdown.\n"
        "3 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Earthquake implementation pending — unsafe AoE bludgeoning "
            "damage + STUNNED condition. Same pattern as Fireball "
            "with condition rider."
        )

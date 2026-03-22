"""
Wrath of God — divine judgement spell, available from GRANDMASTER mastery.
**Paladin only.**

Massive unsafe AoE radiant damage that hits everything in the room
(including caster and allies). Additionally applies BLINDED or STUNNED
to targets.

Scaling:
    GM(5): massive radiant damage + BLINDED/STUNNED, mana 100

Cooldown: 3 rounds (default GM).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class WrathOfGod(Spell):
    key = "wrath_of_god"
    aliases = ["wrath", "wog"]
    name = "Wrath of God"
    school = skills.DIVINE_JUDGEMENT
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "none"
    description = "Calls down the wrath of the divine upon all in the room."
    mechanics = (
        "Unsafe AoE — hits EVERYTHING including caster and allies.\n"
        "Massive radiant damage + BLINDED/STUNNED condition.\n"
        "3 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Wrath of God implementation pending — unsafe AoE radiant "
            "damage + BLINDED/STUNNED condition application. "
            "Same pattern as Fireball but with condition riders."
        )

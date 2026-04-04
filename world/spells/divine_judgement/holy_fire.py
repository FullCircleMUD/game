"""
Holy Fire — divine judgement spell, available from EXPERT mastery.
**Paladin only.**

Safe AoE radiant damage to enemies. The paladin's Fireball equivalent.
Righteous precision — only strikes enemies, never allies.

Diminishing accuracy (safe AoE):
    1st enemy: 100% chance to hit
    2nd enemy:  80% chance to hit
    3rd enemy:  60% chance to hit
    4th enemy:  40% chance to hit
    5th+:       20% chance to hit

Damage scales with mastery tier (+3d6/tier):
    EXPERT(3):  8d6 radiant   (avg 28, mana 28)
    MASTER(4):  11d6 radiant  (avg 39, mana 39)
    GM(5):      14d6 radiant  (avg 49, mana 49)

Cooldown: 1 round (default EXPERT).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class HolyFire(Spell):
    key = "holy_fire"
    aliases = ["hf"]
    name = "Holy Fire"
    school = skills.DIVINE_JUDGEMENT
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    description = "Calls down pillars of holy fire upon enemies in the room."
    mechanics = (
        "Safe AoE — only hits enemies, never you or allies.\n"
        "Diminishing accuracy: 1st enemy 100%, 2nd 80%, 3rd 60%, 4th 40%, 5th+ 20%.\n"
        "Damage: 8d6 (Expert), 11d6 (Master), 14d6 (Grandmaster) radiant.\n"
        "1 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Holy Fire implementation pending — safe AoE radiant damage. "
            "Same pattern as Flame Burst / Cone of Cold."
        )

"""
Bravery — divine judgement spell, available from BASIC mastery.

Self-buff that steels the paladin for battle, granting temporary HP
and an AC bonus. The paladin's pre-combat preparation spell.

Scaling:
    BASIC(1):   +1 AC, +5 temp HP,  5 min,  mana 5
    SKILLED(2): +1 AC, +10 temp HP, 10 min, mana 8
    EXPERT(3):  +2 AC, +15 temp HP, 10 min, mana 12
    MASTER(4):  +2 AC, +20 temp HP, 15 min, mana 16
    GM(5):      +3 AC, +25 temp HP, 15 min, mana 20

Cannot stack with itself. Temp HP does not stack — higher value wins.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Bravery(Spell):
    key = "bravery"
    aliases = ["brave"]
    name = "Bravery"
    school = skills.DIVINE_JUDGEMENT
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 12, 4: 16, 5: 20}
    target_type = "self"
    cooldown = 0
    description = "Steels the caster with divine courage, bolstering armour and vitality."
    mechanics = (
        "Self-buff — grants AC bonus and temporary HP.\n"
        "Basic: +1 AC, +5 temp HP / 5 min. Skilled: +1 AC, +10 / 10 min.\n"
        "Expert: +2 AC, +15 / 10 min. Master: +2 AC, +20 / 15 min.\n"
        "Grandmaster: +3 AC, +25 / 15 min.\n"
        "Cannot stack with itself. Temp HP does not stack.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Bravery implementation pending — needs BRAVERY NamedEffect entry, "
            "AC stat_bonus, temporary HP system (or hp_max bonus), "
            "seconds-based timer, anti-stacking check."
        )

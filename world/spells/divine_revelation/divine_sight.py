"""
Divine Sight — divine revelation spell, available from BASIC mastery.

Grants DARKVISION condition through divine blessing. The cleric
equivalent of the mage's Infravision spell.

Scaling (duration only):
    BASIC(1):   30 min,  mana 3
    SKILLED(2): 1 hour,  mana 5
    EXPERT(3):  2 hours, mana 7
    MASTER(4):  3 hours, mana 9
    GM(5):      4 hours, mana 12

Recasting refreshes duration.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DivineSight(Spell):
    key = "divine_sight"
    aliases = ["dsight"]
    name = "Divine Sight"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    cooldown = 0
    description = "Blesses the caster with the ability to see in total darkness."
    mechanics = (
        "Grants DARKVISION — see normally in dark rooms.\n"
        "Duration: 30 min (Basic) to 4 hours (GM).\n"
        "Recasting refreshes the duration.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Divine Sight implementation pending — needs DARKVISION condition "
            "applied as a named effect with seconds-based timer."
        )

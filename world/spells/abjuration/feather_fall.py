"""
Feather Fall — abjuration spell, available from BASIC mastery.

Negates fall damage for the caster. When FLY is removed while
airborne or when falling from a climbable fixture, the caster
floats gently to the ground instead of taking damage.

Scaling (duration):
    BASIC(1):   10 min,  mana 3
    SKILLED(2): 30 min,  mana 5
    EXPERT(3):  1 hour,  mana 7
    MASTER(4):  2 hours, mana 9
    GM(5):      4 hours, mana 12

Self-buff. Recasting refreshes duration.
Does NOT grant flight — just prevents the consequences of falling.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class FeatherFall(Spell):
    key = "feather_fall"
    aliases = ["ffall", "feather"]
    name = "Feather Fall"
    school = skills.ABJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    cooldown = 0
    description = "Protects the caster from fall damage."
    mechanics = (
        "Negates fall damage when FLY is lost while airborne.\n"
        "Does NOT grant flight.\n"
        "Duration: 10 min (Basic) to 4 hours (GM).\n"
        "Recasting refreshes duration.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Feather Fall implementation pending — needs FEATHER_FALL "
            "named effect checked in the FLY removal fall damage path "
            "(FCMCharacter.remove_condition FLY handler)."
        )

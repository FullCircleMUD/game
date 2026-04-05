"""
Water Breathing — nature magic spell, available from BASIC mastery.

Grants the WATER_BREATHING condition, allowing the target to breathe
underwater indefinitely. Removes any active breath timer.

Scaling (duration):
    BASIC(1):   10 min,  mana 4
    SKILLED(2): 30 min,  mana 6
    EXPERT(3):  1 hour,  mana 8
    MASTER(4):  2 hours, mana 10
    GM(5):      4 hours, mana 14

Can be cast on self or ally. Recasting refreshes duration.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class WaterBreathing(Spell):
    key = "water_breathing"
    aliases = ["wbreathe", "wb"]
    name = "Water Breathing"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "friendly"
    cooldown = 0
    description = "Grants the ability to breathe underwater."
    mechanics = (
        "Grants WATER_BREATHING condition — breathe underwater.\n"
        "Removes any active breath timer.\n"
        "Duration: 10 min (Basic) to 4 hours (GM).\n"
        "Can target self or ally. Recasting refreshes duration.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Water Breathing implementation pending — needs WATER_BREATHING "
            "condition applied as named effect with seconds-based timer, "
            "cancel any active BreathTimerScript on target."
        )

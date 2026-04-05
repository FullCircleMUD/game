"""
Blindness — divine dominion spell, available from BASIC mastery.

Inflicts BLINDED on a single target. Blinded creatures have
disadvantage on all attack rolls. Contested WIS vs CON save.

Scaling (duration):
    BASIC(1):   3 rounds,  mana 5
    SKILLED(2): 4 rounds,  mana 7
    EXPERT(3):  5 rounds,  mana 9
    MASTER(4):  6 rounds,  mana 12
    GM(5):      8 rounds,  mana 15

Contested WIS (caster) vs CON (target). HUGE+ immune.
Save-each-round to break early.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Blindness(Spell):
    key = "blindness"
    aliases = ["blind"]
    name = "Blindness"
    school = skills.DIVINE_DOMINION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 7, 3: 9, 4: 12, 5: 15}
    target_type = "hostile"
    cooldown = 0
    description = "Strikes a creature blind with divine authority."
    mechanics = (
        "Inflicts BLINDED — disadvantage on all attack rolls.\n"
        "Contested WIS vs CON save. HUGE+ immune.\n"
        "Save-each-round (CON) to break early.\n"
        "Duration: 3 rounds (Basic) to 8 rounds (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Blindness implementation pending — needs BLINDED condition "
            "applied as named effect with combat_rounds duration, "
            "contested WIS vs CON, save-each-round, size gating, "
            "disadvantage enforcement in combat handler."
        )

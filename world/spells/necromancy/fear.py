"""
Fear — necromancy spell, available from BASIC mastery.

Inflicts FRIGHTENED on a single target, causing them to flee in
terror. Contested WIS vs WIS save.

Scaling (duration):
    BASIC(1):   1 round,  mana 4
    SKILLED(2): 2 rounds, mana 6
    EXPERT(3):  3 rounds, mana 8
    MASTER(4):  4 rounds, mana 10
    GM(5):      5 rounds, mana 14

FRIGHTENED: target flees through a random exit each round.
Save-each-round (WIS) to break early. HUGE+ immune.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Fear(Spell):
    key = "fear"
    aliases = ["scare"]
    name = "Fear"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "hostile"
    cooldown = 0
    description = "Fills a creature with supernatural terror, causing it to flee."
    mechanics = (
        "Inflicts FRIGHTENED — target flees through a random exit each round.\n"
        "Contested WIS vs WIS. Save-each-round to break early.\n"
        "HUGE+ immune.\n"
        "Duration: 1 round (Basic) to 5 rounds (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Fear implementation pending — needs FRIGHTENED condition or "
            "named effect, forced flee each round (random exit), "
            "contested WIS vs WIS, save-each-round, size gating."
        )

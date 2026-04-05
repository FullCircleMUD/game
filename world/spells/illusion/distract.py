"""
Distract — illusion spell, available from BASIC mastery.

Creates an illusory flash or noise that momentarily distracts enemies.
In combat: gives the caster advantage on their next action.
Out of combat: gives non-combat advantage (next skill check).

Scaling:
    BASIC(1):   1 round advantage,  mana 3
    SKILLED(2): 1 round advantage,  mana 4
    EXPERT(3):  2 rounds advantage, mana 6
    MASTER(4):  2 rounds advantage, mana 8
    GM(5):      3 rounds advantage, mana 10

Also allows flee attempts without the usual DEX check (auto-success)
for the round the distraction is active.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Distract(Spell):
    key = "distract"
    aliases = ["dist"]
    name = "Distract"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 4, 3: 6, 4: 8, 5: 10}
    target_type = "none"
    cooldown = 0
    description = "Creates an illusory distraction, giving the caster an opening."
    mechanics = (
        "In combat: grants caster advantage for 1-3 rounds.\n"
        "Out of combat: grants non-combat advantage (next skill check).\n"
        "Also allows auto-success flee while active.\n"
        "Duration: 1 round (Basic) to 3 rounds (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Distract implementation pending — needs combat advantage "
            "via set_advantage() on all enemies for N rounds, or "
            "non_combat_advantage flag out of combat, auto-flee flag."
        )

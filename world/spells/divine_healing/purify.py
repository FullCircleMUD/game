"""
Purify — divine healing spell, available from SKILLED mastery.

Removes a harmful condition from the target (poison, disease, etc.).
The cleric's condition-removal utility spell.

Scaling:
    SKILLED(2): mana TBD
    EXPERT(3):  mana TBD
    MASTER(4):  mana TBD
    GM(5):      mana TBD

Cooldown: 0 (default SKILLED).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Purify(Spell):
    key = "purify"
    aliases = ["pur"]
    name = "Purify"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 10, 3: 14, 4: 18, 5: 22}
    target_type = "friendly"
    description = "Purges a harmful condition from the target."
    mechanics = (
        "Removes a single harmful condition (poison, disease, etc.).\n"
        "Syntax: cast purify <target>\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Purify implementation pending — needs condition removal "
            "mechanics (which conditions are purgeable, priority order)."
        )

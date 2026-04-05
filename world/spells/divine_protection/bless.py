"""
Bless — divine protection spell, available from BASIC mastery.

Buffs a single target (self or ally) with a bonus to hit rolls and
saving throws. The bread-and-butter cleric combat support buff.

Scaling:
    BASIC(1):   +1 hit, 3 min,  mana 4
    SKILLED(2): +1 hit, 5 min,  mana 6
    EXPERT(3):  +2 hit, 5 min,  mana 8
    MASTER(4):  +2 hit, 10 min, mana 10
    GM(5):      +3 hit, 10 min, mana 14

Cannot stack with itself. Recasting refreshes if new duration is longer.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Bless(Spell):
    key = "bless"
    aliases = ["ble"]
    name = "Bless"
    school = skills.DIVINE_PROTECTION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "friendly"
    cooldown = 0
    description = "Blesses a target with divine favour, improving their combat prowess."
    mechanics = (
        "Grants a bonus to hit rolls and saving throws.\n"
        "Basic: +1 / 3 min. Skilled: +1 / 5 min. Expert: +2 / 5 min.\n"
        "Master: +2 / 10 min. Grandmaster: +3 / 10 min.\n"
        "Cannot stack with itself. Recasting refreshes duration.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Bless implementation pending — needs BLESSED NamedEffect entry, "
            "stat_bonus on total_hit_bonus, seconds-based timer, "
            "anti-stacking check."
        )

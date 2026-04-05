"""
Bless — divine protection spell, available from BASIC mastery.

Buffs a single target (self or ally) with a bonus to hit rolls and
save-each-round rolls. The bread-and-butter cleric combat support buff.

Scaling:
    BASIC(1):   +1 hit/save, 1 min,  mana 4
    SKILLED(2): +1 hit/save, 2 min,  mana 5
    EXPERT(3):  +2 hit/save, 2 min,  mana 6
    MASTER(4):  +2 hit/save, 3 min,  mana 7
    GM(5):      +3 hit/save, 3 min,  mana 8

Cannot stack with itself. Recasting while active refunds mana.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# (bonus, duration_minutes) per tier
_SCALING = {
    1: (1, 1),
    2: (1, 2),
    3: (2, 2),
    4: (2, 3),
    5: (3, 3),
}


@register_spell
class Bless(Spell):
    key = "bless"
    aliases = ["ble"]
    name = "Bless"
    school = skills.DIVINE_PROTECTION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 5, 3: 6, 4: 7, 5: 8}
    target_type = "friendly"
    cooldown = 0
    description = "Blesses a target with divine favour, improving their combat prowess."
    mechanics = (
        "Grants a bonus to hit rolls and save-each-round rolls.\n"
        "Basic: +1 / 1 min. Skilled: +1 / 2 min. Expert: +2 / 2 min.\n"
        "Master: +2 / 3 min. Grandmaster: +3 / 3 min.\n"
        "Cannot stack with itself.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        if target.has_effect("blessed"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            name = "Your" if target == caster else f"{target.key}'s"
            return (False, {
                "first": f"{name} blessing is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        bonus, duration_minutes = _SCALING.get(tier, (1, 1))
        duration_seconds = duration_minutes * 60

        target.apply_blessed(bonus, bonus, duration_seconds)

        min_s = "minute" if duration_minutes == 1 else "minutes"
        if target == caster:
            return (True, {
                "first": (
                    f"|WDivine favour fills you! "
                    f"(+{bonus} hit/save, {duration_minutes} {min_s})|n"
                ),
                "second": None,
                "third": (
                    f"|W{caster.key} glows briefly with divine favour.|n"
                ),
            })
        return (True, {
            "first": (
                f"|WYou bless {target.key} with divine favour! "
                f"(+{bonus} hit/save, {duration_minutes} {min_s})|n"
            ),
            "second": (
                f"|W{caster.key} blesses you with divine favour! "
                f"(+{bonus} hit/save, {duration_minutes} {min_s})|n"
            ),
            "third": (
                f"|W{caster.key} blesses {target.key} with divine favour.|n"
            ),
        })

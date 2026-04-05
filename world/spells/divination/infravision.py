"""
Darkvision — divination spell, available from BASIC mastery.

Grants DARKVISION condition, allowing the caster to see in darkness
without a light source. Long-duration utility buff.

Scaling (duration only):
    BASIC(1):   30 min,  mana 3
    SKILLED(2): 1 hour,  mana 5
    EXPERT(3):  2 hours, mana 7
    MASTER(4):  3 hours, mana 9
    GM(5):      4 hours, mana 12

Shares DARKVISION_BUFF effect with Divine Sight (cannot stack).
Recasting while active refunds mana.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Duration in minutes per tier
_DURATION_MINUTES = {1: 30, 2: 60, 3: 120, 4: 180, 5: 240}


@register_spell
class Darkvision(Spell):
    key = "darkvision"
    aliases = ["dv", "infra"]
    name = "Darkvision"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    cooldown = 0
    description = "Magically enhances vision to see in total darkness."
    mechanics = (
        "Grants DARKVISION — see normally in dark rooms.\n"
        "Duration: 30 min (Basic) to 4 hours (GM).\n"
        "Cannot stack with Divine Sight (shared effect).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        if caster.has_effect("darkvision_buff"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your darkvision is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration_minutes = _DURATION_MINUTES.get(tier, 30)
        duration_seconds = duration_minutes * 60

        caster.apply_darkvision_buff(duration_seconds)

        if duration_minutes >= 60:
            hours = duration_minutes // 60
            time_str = f"{hours} {'hour' if hours == 1 else 'hours'}"
        else:
            time_str = f"{duration_minutes} minutes"

        return (True, {
            "first": (
                f"|MYour eyes tingle with arcane energy. You can now see "
                f"in total darkness! ({time_str})|n"
            ),
            "second": None,
            "third": (
                f"|M{caster.key}'s eyes gleam faintly with arcane energy.|n"
            ),
        })

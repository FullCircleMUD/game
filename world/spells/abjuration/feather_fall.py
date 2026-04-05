"""
Feather Fall — abjuration spell, available from BASIC mastery.

Negates fall damage for the caster. When FLY is removed while
airborne or when falling from height, the caster floats gently
to the ground instead of taking damage.

Scaling (duration only):
    BASIC(1):   10 min,  mana 3
    SKILLED(2): 30 min,  mana 5
    EXPERT(3):  1 hour,  mana 7
    MASTER(4):  2 hours, mana 9
    GM(5):      4 hours, mana 12

Self-buff. Does NOT grant flight — just prevents fall damage.
Recasting while active refunds mana.
"""

from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Duration in minutes per tier
_DURATION_MINUTES = {1: 10, 2: 30, 3: 60, 4: 120, 5: 240}


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
        "Negates fall damage when losing flight or falling from height.\n"
        "Does NOT grant flight.\n"
        "Duration: 10 min (Basic) to 4 hours (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        if caster.has_effect("feather_fall"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your Feather Fall is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration_minutes = _DURATION_MINUTES.get(tier, 10)
        duration_seconds = duration_minutes * 60

        caster.apply_named_effect(
            NamedEffect.FEATHER_FALL,
            duration=duration_seconds,
        )

        if duration_minutes >= 60:
            hours = duration_minutes // 60
            time_str = f"{hours} {'hour' if hours == 1 else 'hours'}"
        else:
            time_str = f"{duration_minutes} minutes"

        return (True, {
            "first": (
                f"|CYou feel light as a feather. Falls can no longer "
                f"harm you! ({time_str})|n"
            ),
            "second": None,
            "third": (
                f"|C{caster.key} seems to become lighter on their feet.|n"
            ),
        })

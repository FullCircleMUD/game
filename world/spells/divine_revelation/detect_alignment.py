"""
Detect Alignment — divine revelation spell, available from BASIC mastery.

Grants the caster the ability to see alignment auras on creatures in
room descriptions. Evil creatures show a red (Evil) tag, good show
gold (Good), neutral show white (Neutral).

Scaling (duration only):
    BASIC(1):   30 min,  mana 2
    SKILLED(2): 1 hour,  mana 3
    EXPERT(3):  2 hours, mana 4
    MASTER(4):  3 hours, mana 5
    GM(5):      4 hours, mana 8

Self-buff. Recasting while active refunds mana.
"""

from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Duration in minutes per tier
_DURATION_MINUTES = {1: 30, 2: 60, 3: 120, 4: 180, 5: 240}


@register_spell
class DetectAlignment(Spell):
    key = "detect_alignment"
    aliases = ["dalign", "detect align"]
    name = "Detect Alignment"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 2, 2: 3, 3: 4, 4: 5, 5: 8}
    target_type = "self"
    cooldown = 0
    description = "Divinely reveals the alignment of creatures around you."
    mechanics = (
        "Self-buff — see alignment auras on creatures in the room.\n"
        "Evil: red (Evil) tag. Good: gold (Good) tag. Neutral: white.\n"
        "Duration: 30 min (Basic) to 4 hours (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        if caster.has_effect("detect_alignment"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your alignment sight is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration_minutes = _DURATION_MINUTES.get(tier, 30)
        duration_seconds = duration_minutes * 60

        caster.apply_named_effect(
            NamedEffect.DETECT_ALIGNMENT,
            duration=duration_seconds,
        )

        if duration_minutes >= 60:
            hours = duration_minutes // 60
            time_str = f"{hours} {'hour' if hours == 1 else 'hours'}"
        else:
            time_str = f"{duration_minutes} minutes"

        return (True, {
            "first": (
                f"|WDivine insight fills your eyes. You can now sense "
                f"the alignment of those around you! ({time_str})|n"
            ),
            "second": None,
            "third": (
                f"|W{caster.key}'s eyes glow briefly with divine insight.|n"
            ),
        })

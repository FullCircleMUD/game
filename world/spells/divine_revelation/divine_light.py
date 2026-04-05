"""
Divine Light — divine revelation spell, available from BASIC mastery.

Conjures a hovering sphere of holy radiance that illuminates the room
for everyone. Follows the caster — no held slot, no fuel.

Scaling (duration only — light is binary):
    BASIC(1):   30 min,  mana 3
    SKILLED(2): 1 hour,  mana 5
    EXPERT(3):  2 hours, mana 7
    MASTER(4):  3 hours, mana 9
    GM(5):      4 hours, mana 12

Shares LIGHT_SPELL effect with Light (cannot stack).
Recasting while active refunds mana.
"""

from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Duration in minutes per tier
_DURATION_MINUTES = {1: 30, 2: 60, 3: 120, 4: 180, 5: 240}


@register_spell
class DivineLight(Spell):
    key = "divine_light"
    aliases = ["dlight"]
    name = "Divine Light"
    school = skills.DIVINE_REVELATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    cooldown = 0
    description = "Conjures a sphere of holy radiance that illuminates the area."
    mechanics = (
        "Conjures a divine light that illuminates the room for everyone.\n"
        "Follows the caster from room to room.\n"
        "Duration: 30 min (Basic) to 4 hours (GM).\n"
        "Cannot stack with Light (shared effect).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        if caster.has_effect("light_spell"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your light spell is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration_minutes = _DURATION_MINUTES.get(tier, 30)
        duration_seconds = duration_minutes * 60

        caster.apply_named_effect(
            NamedEffect.LIGHT_SPELL,
            duration=duration_seconds,
        )

        if duration_minutes >= 60:
            hours = duration_minutes // 60
            time_str = f"{hours} {'hour' if hours == 1 else 'hours'}"
        else:
            time_str = f"{duration_minutes} minutes"

        return (True, {
            "first": (
                f"|WA sphere of holy radiance appears, bathing "
                f"the area in warm light! ({time_str})|n"
            ),
            "second": None,
            "third": (
                f"|WA sphere of holy radiance appears around "
                f"{caster.key}, bathing the area in warm light.|n"
            ),
        })

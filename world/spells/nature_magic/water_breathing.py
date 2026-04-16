"""
Water Breathing — nature magic spell, available from BASIC mastery.

Grants the WATER_BREATHING condition, allowing the target to breathe
underwater indefinitely for the duration. Removes any active breath
timer on cast.

Scaling (duration only):
    BASIC(1):   10 min,  mana 4
    SKILLED(2): 30 min,  mana 6
    EXPERT(3):  1 hour,  mana 8
    MASTER(4):  2 hours, mana 10
    GM(5):      4 hours, mana 14

Can be cast on self or ally. Recasting while active refunds mana.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Duration in minutes per tier
_DURATION_MINUTES = {1: 10, 2: 30, 3: 60, 4: 120, 5: 240}


@register_spell
class WaterBreathing(Spell):
    key = "water_breathing"
    aliases = ["wbreathe", "wb"]
    name = "Water Breathing"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "actor_friendly"
    cooldown = 0
    description = "Grants the ability to breathe underwater."
    mechanics = (
        "Grants WATER_BREATHING — breathe underwater, no drowning.\n"
        "Removes any active breath timer on cast.\n"
        "Duration: 10 min (Basic) to 4 hours (GM).\n"
        "Can target self or ally.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        if target.has_effect("water_breathing_buff"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            name = "Your" if target == caster else f"{target.key}'s"
            return (False, {
                "first": f"{name} water breathing is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        duration_minutes = _DURATION_MINUTES.get(tier, 10)
        duration_seconds = duration_minutes * 60

        target.apply_water_breathing_buff(duration_seconds)

        # Cancel any active breath timer (drowning countdown)
        breath_scripts = target.scripts.get("breath_timer")
        if breath_scripts:
            breath_scripts[0].delete()

        if duration_minutes >= 60:
            hours = duration_minutes // 60
            time_str = f"{hours} {'hour' if hours == 1 else 'hours'}"
        else:
            time_str = f"{duration_minutes} minutes"

        if target == caster:
            return (True, {
                "first": (
                    f"|CYou feel the power of nature fill your lungs. "
                    f"You can breathe underwater! ({time_str})|n"
                ),
                "second": None,
                "third": (
                    f"|C{caster.key}'s breathing changes as nature's "
                    f"power fills their lungs.|n"
                ),
            })
        return (True, {
            "first": (
                f"|CYou channel nature's power into {target.key}. "
                f"They can breathe underwater! ({time_str})|n"
            ),
            "second": (
                f"|C{caster.key} channels nature's power into you. "
                f"You can breathe underwater! ({time_str})|n"
            ),
            "third": (
                f"|C{caster.key} channels nature's power into {target.key}, "
                f"granting them the ability to breathe underwater.|n"
            ),
        })

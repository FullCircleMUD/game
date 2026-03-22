"""
Sanctuary — divine protection spell, available from BASIC mastery.

Self-buff that prevents enemies from targeting the caster. Breaks
immediately if the caster performs any offensive action (attack, hostile
spell, etc.). Uses the existing SANCTUARY condition + named effect system.

Recasting refreshes the duration if the new cast would grant more time
than the remaining duration. If the existing effect is stronger, the
recast is skipped and mana is refunded.

Scaling:
    BASIC(1):   60s  (1 min),  mana 5
    SKILLED(2): 120s (2 min),  mana 8
    EXPERT(3):  180s (3 min),  mana 10
    MASTER(4):  240s (4 min),  mana 14
    GM(5):      300s (5 min),  mana 16

Cooldown: 0 (duration-limited buff, breaks on action).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Sanctuary(Spell):
    key = "sanctuary"
    aliases = ["sanc"]
    name = "Sanctuary"
    school = skills.DIVINE_PROTECTION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "self"
    cooldown = 0
    description = "Surrounds the caster with a holy ward that prevents enemies from targeting them."
    mechanics = (
        "Self-buff — enemies cannot target you.\n"
        "Breaks immediately if you attack or cast an offensive spell.\n"
        "Recasting refreshes the duration (only if gaining time).\n"
        "Duration: 1min (Basic) to 5min (GM).\n"
        "No cooldown."
    )

    # Duration in minutes per tier
    _DURATION = {
        1: 1,
        2: 2,
        3: 3,
        4: 4,
        5: 5,
    }

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        duration_minutes = self._DURATION.get(tier, 1)
        duration_seconds = duration_minutes * 60

        # Only refresh if gaining time (don't downgrade a longer-duration cast)
        if caster.has_effect("sanctuary"):
            remaining = caster.get_effect_remaining_seconds("sanctuary")
            if remaining is not None and remaining >= duration_seconds:
                # Refund mana (base_spell.cast deducts BEFORE _execute)
                cost = self.mana_cost.get(tier, 0)
                caster.mana += cost
                return (False, {
                    "first": "|WYour existing sanctuary is stronger — no effect.|n",
                    "second": None,
                    "third": None,
                })
            caster.remove_named_effect("sanctuary")

        caster.apply_sanctuary(duration_seconds)

        min_s = "minute" if duration_minutes == 1 else "minutes"
        return (True, {
            "first": (
                f"|WYou invoke divine sanctuary! A holy ward surrounds you. "
                f"({duration_minutes} {min_s})|n"
            ),
            "second": None,  # self-cast
            "third": (
                f"|W{caster.key} is surrounded by a shimmering divine ward!|n"
            ),
        })

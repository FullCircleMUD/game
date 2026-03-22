"""
Invisibility — illusion spell, available from SKILLED mastery.

Standard invisibility — caster becomes invisible but the effect
breaks on attacking or casting an offensive spell. Uses the existing
INVISIBLE condition.

Good for scouting, sneaking past enemies, and setting up ambushes.
Attacking from invisibility grants advantage (like attacking from HIDDEN).

Recasting refreshes the duration if the new cast would grant more time
than the remaining duration. If the existing effect is stronger, the
recast is skipped and mana is refunded.

Scaling:
    SKILLED(2): 5 minutes duration,  mana 15
    EXPERT(3):  10 minutes duration, mana 25
    MASTER(4):  30 minutes duration, mana 40
    GM(5):      60 minutes duration, mana 40

Cooldown: 0 (duration-limited buff, breaks on action).

Recast refreshes duration via remove-then-reapply (only if gaining time).
Break-on-action zeros all refs (see break_invisibility() on
EffectsManagerMixin).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Invisibility(Spell):
    key = "invisibility"
    aliases = ["invis"]
    name = "Invisibility"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 15, 3: 25, 4: 40, 5: 40}
    target_type = "self"
    cooldown = 0
    description = "Become invisible — breaks when you attack or cast an offensive spell."
    mechanics = (
        "Self-buff — uses existing INVISIBLE condition.\n"
        "Invisible to all without DETECT_INVIS.\n"
        "Breaks on attacking or casting an offensive spell.\n"
        "Attacking from invisibility grants 1 round advantage.\n"
        "Duration: 5min (Skilled) to 60min (GM).\n"
        "No cooldown. No anti-stacking (condition-only, no stat impact)."
    )

    # Duration in minutes per tier
    _DURATION = {
        2: 5,
        3: 10,
        4: 30,
        5: 60,
    }

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        duration_minutes = self._DURATION.get(tier, 5)
        duration_seconds = duration_minutes * 60

        # Refresh: only if gaining time (don't downgrade a longer-duration cast)
        if caster.has_effect("invisible"):
            remaining = caster.get_effect_remaining_seconds("invisible")
            if remaining is not None and remaining >= duration_seconds:
                # Refund mana (base_spell.cast deducts BEFORE _execute)
                cost = self.mana_cost.get(tier, 0)
                caster.mana += cost
                return (False, {
                    "first": "|CYour existing invisibility is stronger — no effect.|n",
                    "second": None,
                    "third": None,
                })
            caster.remove_named_effect("invisible")

        caster.apply_invisible(duration_seconds)

        min_s = "minute" if duration_minutes == 1 else "minutes"
        return (True, {
            "first": (
                f"|CYour body shimmers and fades from sight. "
                f"You are now invisible! "
                f"({duration_minutes} {min_s})|n"
            ),
            "second": None,  # self-cast
            "third": (
                f"|C{caster.key}'s body shimmers and fades from sight!|n"
            ),
        })

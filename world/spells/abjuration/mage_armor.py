"""
Mage Armor — abjuration spell, available from BASIC mastery.

Long-duration AC buff for mages. Provides a modest AC bonus that lasts
for hours, making it the go-to pre-combat preparation spell. Stacks
with Shield for strong combined defense at high tiers.

Scaling (AC bonus and duration alternate each tier):
    BASIC(1):   +3 AC, 1 hour,  mana 3
    SKILLED(2): +3 AC, 2 hours, mana 5
    EXPERT(3):  +4 AC, 2 hours, mana 7
    MASTER(4):  +4 AC, 3 hours, mana 9
    GM(5):      +5 AC, 3 hours, mana 12

Cheap mana cost — this is a maintenance buff, not a combat spike.
Cannot stack with itself (has_effect anti-stacking check).

Combined with Shield at GM: +5 (armor) + +6 (shield) = +11 AC total.

Uses EffectsManagerMixin named effect system with seconds-based timer
(wall-clock duration, not combat rounds).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class MageArmor(Spell):
    key = "mage_armor"
    aliases = ["ma", "armor"]
    name = "Mage Armor"
    school = skills.ABJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "self"
    spell_range = "self"
    cooldown = 0
    description = "Wraps you in an invisible layer of magical protection."
    mechanics = (
        "Grants an AC bonus for an extended duration (hours).\n"
        "Basic: +3 AC / 1 hour. Skilled: +3 / 2 hours. Expert: +4 / 2 hours.\n"
        "Master: +4 / 3 hours. Grandmaster: +5 / 3 hours.\n"
        "Cannot stack with itself — recasting while active has no effect.\n"
        "Stacks with Shield for combined AC bonus."
    )

    # (AC bonus, duration in hours) per tier
    _SCALING = {
        1: (3, 1),
        2: (3, 2),
        3: (4, 2),
        4: (4, 3),
        5: (5, 3),
    }

    def _execute(self, caster, target):
        # Anti-stacking — can't recast while active
        if caster.has_effect("mage_armored"):
            # Refund mana (base class deducts before calling _execute)
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "Your Mage Armor is already active.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        ac_bonus, duration_hours = self._SCALING.get(tier, (3, 1))
        duration_seconds = duration_hours * 3600

        caster.apply_mage_armor(ac_bonus, duration_seconds)

        hour_s = "hour" if duration_hours == 1 else "hours"
        return (True, {
            "first": (
                f"|CA shimmering layer of magical protection wraps around you! "
                f"(+{ac_bonus} AC, {duration_hours} {hour_s})|n"
            ),
            "second": None,
            "third": (
                f"|C{caster.key} is enveloped in a shimmering layer of "
                f"magical protection.|n"
            ),
        })

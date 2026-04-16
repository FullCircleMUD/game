"""
Divine Armor — divine protection spell, available from BASIC mastery.

Long-duration AC buff for clerics/paladins. The divine equivalent of
Mage Armor — shares the same ARMORED named effect so they cannot stack.

Scaling (AC bonus and duration alternate each tier):
    BASIC(1):   +2 AC, 1 hour,  mana 4
    SKILLED(2): +2 AC, 2 hours, mana 6
    EXPERT(3):  +3 AC, 2 hours, mana 8
    MASTER(4):  +3 AC, 3 hours, mana 10
    GM(5):      +4 AC, 3 hours, mana 14

Slightly weaker AC than Mage Armor (+2/+4 vs +3/+5) but clerics have
shields and heavier base equipment to compensate.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DivineArmor(Spell):
    key = "divine_armor"
    aliases = ["da", "darmor"]
    name = "Divine Armor"
    school = skills.DIVINE_PROTECTION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "self"
    range = "self"
    cooldown = 0
    description = "Wraps the caster in a shimmering layer of divine protection."
    mechanics = (
        "Grants an AC bonus for an extended duration (hours).\n"
        "Basic: +2 AC / 1 hour. Skilled: +2 / 2 hours. Expert: +3 / 2 hours.\n"
        "Master: +3 / 3 hours. Grandmaster: +4 / 3 hours.\n"
        "Cannot stack with Mage Armor — both use the same effect.\n"
        "Stacks with Shield for combined AC bonus."
    )

    # (AC bonus, duration in hours) per tier
    _SCALING = {
        1: (2, 1),
        2: (2, 2),
        3: (3, 2),
        4: (3, 3),
        5: (4, 3),
    }

    def _execute(self, caster, target):
        # Anti-stacking — shared with Mage Armor
        if caster.has_effect("armored"):
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            return (False, {
                "first": "You are already protected by an armor spell.",
                "second": None,
                "third": None,
            })

        tier = self.get_caster_tier(caster)
        ac_bonus, duration_hours = self._SCALING.get(tier, (2, 1))
        duration_seconds = duration_hours * 3600

        caster.apply_armor_buff(ac_bonus, duration_seconds)

        hour_s = "hour" if duration_hours == 1 else "hours"
        return (True, {
            "first": (
                f"|WA shimmering layer of divine protection wraps around you! "
                f"(+{ac_bonus} AC, {duration_hours} {hour_s})|n"
            ),
            "second": None,
            "third": (
                f"|W{caster.key} is enveloped in a shimmering layer of "
                f"divine protection.|n"
            ),
        })

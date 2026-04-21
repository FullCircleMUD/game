"""
Bolt of Judgement — divine judgement spell, available from BASIC mastery.

Hurls a bolt of radiant energy at a target. Auto-hit (like Magic
Missile). Base damage scales like Magic Missile (tier x 1d4+1), but
damage is multiplied against evil targets based on how evil they are.

Multiplier formula: max(1, ceil(-target.alignment_score / 250))

    Good/Neutral (0 to +1000):     1x
    Slightly evil (-1 to -250):    1x
    Evil (-251 to -500):           2x
    Very evil (-501 to -750):      3x
    Pure evil (-751 to -1000):     4x

Scaling (base damage before multiplier):
    BASIC(1):   1d4+1 radiant,  mana 3
    SKILLED(2): 2d4+2 radiant,  mana 5
    EXPERT(3):  3d4+3 radiant,  mana 7
    MASTER(4):  4d4+4 radiant,  mana 9
    GM(5):      5d4+5 radiant,  mana 12

Auto-hit. No cooldown. Radiant damage type.
"""

import math

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


@register_spell
class BoltOfJudgement(Spell):
    key = "bolt_of_judgement"
    aliases = ["boj", "judgement", "bolt judgement"]
    name = "Bolt of Judgement"
    school = skills.DIVINE_JUDGEMENT
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Hurls a bolt of radiant judgement that punishes the wicked."
    mechanics = (
        "Auto-hit radiant damage. Scales like Magic Missile (tier x 1d4+1).\n"
        "Damage multiplied against evil targets based on alignment:\n"
        "  Neutral/good: 1x. Evil: 2x. Very evil: 3x. Pure evil: 4x.\n"
        "No cooldown."
    )

    def _get_evil_multiplier(self, target):
        """Calculate damage multiplier based on target alignment."""
        alignment = getattr(target, "alignment_score", 0)
        if alignment >= 0:
            return 1
        return max(1, math.ceil(-alignment / 250))

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # Roll base damage (same as Magic Missile)
        base_damage = 0
        for _ in range(tier):
            base_damage += dice.roll("1d4+1")

        # Apply evil multiplier
        multiplier = self._get_evil_multiplier(target)
        raw_damage = base_damage * multiplier

        actual_damage = apply_spell_damage(target, raw_damage, DamageType.RADIANT, caster=caster)

        # Build messages
        bolt_s = "bolt" if tier == 1 else "bolts"
        mult_str = ""
        if multiplier > 1:
            mult_str = f" |W(x{multiplier} — divine judgement!)|n"

        return (True, {
            "first": (
                f"You raise your hand in judgement and {tier} {bolt_s} of "
                f"radiant light streak toward {target.key}, "
                f"dealing |r{actual_damage}|n radiant damage!{mult_str}"
            ),
            "second": (
                f"{caster.key} raises a hand in judgement — {tier} {bolt_s} of "
                f"radiant light sear into you, "
                f"dealing |r{actual_damage}|n radiant damage!{mult_str}"
            ),
            "third": (
                f"{caster.key} raises a hand in judgement — {tier} {bolt_s} of "
                f"radiant light streak toward {target.key}, "
                f"dealing |r{actual_damage}|n radiant damage!"
            ),
        })

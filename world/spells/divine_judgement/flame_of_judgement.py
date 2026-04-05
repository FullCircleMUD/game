"""
Flame of Judgement — divine judgement spell, available from BASIC mastery.

Hurls a bolt of holy fire at a single target. Deals radiant damage
with bonus damage against evil-aligned creatures (alignment < 0).

Scaling (base damage, 1 bolt per tier like Magic Missile):
    BASIC(1):   1d4+1 radiant,  mana 3
    SKILLED(2): 2d4+2 radiant,  mana 5
    EXPERT(3):  3d4+3 radiant,  mana 7
    MASTER(4):  4d4+4 radiant,  mana 9
    GM(5):      5d4+5 radiant,  mana 12

Against evil targets (alignment < 0): damage x1.5 (rounded down).
Auto-hit (like Magic Missile). No cooldown.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class FlameOfJudgement(Spell):
    key = "flame_of_judgement"
    aliases = ["foj", "flame judgement"]
    name = "Flame of Judgement"
    school = skills.DIVINE_JUDGEMENT
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "hostile"
    cooldown = 0
    description = "Hurls a bolt of holy fire that burns the wicked."
    mechanics = (
        "Auto-hit radiant damage. 1-5 bolts scaling with tier (1d4+1 each).\n"
        "Against evil targets (alignment < 0): damage x1.5.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Flame of Judgement implementation pending — needs radiant "
            "damage roll (tier)d4+tier, alignment check on target for "
            "1.5x multiplier, auto-hit like Magic Missile."
        )

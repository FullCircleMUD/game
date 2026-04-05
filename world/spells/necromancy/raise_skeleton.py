"""
Raise Skeleton — necromancy spell, available from BASIC mastery.

Raises a weak skeleton minion from a corpse in the room. The skeleton
fights alongside the caster until destroyed or the duration expires.

Scaling:
    BASIC(1):   1 skeleton, 2 min,   mana 6
    SKILLED(2): 1 skeleton, 5 min,   mana 8
    EXPERT(3):  2 skeletons, 5 min,  mana 12
    MASTER(4):  2 skeletons, 10 min, mana 16
    GM(5):      3 skeletons, 10 min, mana 20

Requires a corpse in the room (consumed on cast). Skeletons are weak
(low HP, low damage) but draw enemy attacks. Dismissed on duration
end, caster death, or recast. Max count from one cast — not cumulative.

Higher-tier necromancy unlocks stronger undead:
    SKILLED: Raise Dead (zombie — tougher, slower)
    MASTER:  Raise Lich (intelligent, casts spells)
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class RaiseSkeleton(Spell):
    key = "raise_skeleton"
    aliases = ["rskel", "skeleton"]
    name = "Raise Skeleton"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 6, 2: 8, 3: 12, 4: 16, 5: 20}
    target_type = "none"
    cooldown = 0
    description = "Raises a skeleton minion from a corpse to fight for the caster."
    mechanics = (
        "Consumes a corpse in the room to raise a skeleton minion.\n"
        "Basic: 1 skeleton / 2 min. Skilled: 1 / 5 min.\n"
        "Expert: 2 / 5 min. Master: 2 / 10 min. GM: 3 / 10 min.\n"
        "Skeletons are weak but draw attacks.\n"
        "Dismissed on expiry, caster death, or recast.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Raise Skeleton implementation pending — needs corpse detection "
            "in room, skeleton mob typeclass (weak, follows caster, fights "
            "caster's enemies), timed dismiss, count scaling per tier, "
            "pet/minion system."
        )

"""
Holy Aura — divine protection spell, available from EXPERT mastery.

Group defensive buff that grants AC and resistance bonuses to all
allies in the room.

Scaling:
    EXPERT(3):  mana TBD
    MASTER(4):  mana TBD
    GM(5):      mana TBD

Cooldown: 1 round (default EXPERT).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class HolyAura(Spell):
    key = "holy_aura"
    aliases = ["ha"]
    name = "Holy Aura"
    school = skills.DIVINE_PROTECTION
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    description = "Bathes all allies in a holy aura, bolstering their defences."
    mechanics = (
        "Group buff — AC and resistance bonus to all allies in room.\n"
        "Scales with mastery tier.\n"
        "1 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Holy Aura implementation pending — needs group ally detection, "
            "AC bonus application, and resistance buff mechanics."
        )

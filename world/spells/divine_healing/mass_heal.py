"""
Mass Heal — divine healing spell, available from EXPERT mastery.

Heals all allies in the room. The "Fireball of healing" — the party-save
button for clerics and paladins.

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
class MassHeal(Spell):
    key = "mass_heal"
    aliases = ["mheal", "massheal"]
    name = "Mass Heal"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    description = "A wave of divine energy heals all allies in the room."
    mechanics = (
        "Group heal — heals all allies in room.\n"
        "Healing scales with mastery tier and WIS modifier.\n"
        "1 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Mass Heal implementation pending — needs group ally detection "
            "and healing distribution mechanics."
        )

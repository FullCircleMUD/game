"""
Cure Poison — divine healing spell, available from BASIC mastery.

Removes poison effects from a target. At higher tiers, also grants
temporary poison resistance.

Scaling:
    BASIC(1):   Removes poison,                     mana 4
    SKILLED(2): Removes poison,                     mana 6
    EXPERT(3):  Removes poison + 25% resist 5 min,  mana 8
    MASTER(4):  Removes poison + 50% resist 5 min,  mana 10
    GM(5):      Removes poison + 75% resist 10 min, mana 12

No cooldown. Instant effect (resistance is a timed buff).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class CurePoison(Spell):
    key = "cure_poison"
    aliases = ["cpois", "cp"]
    name = "Cure Poison"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}
    target_type = "friendly"
    cooldown = 0
    description = "Purges poison from the target's body through divine power."
    mechanics = (
        "Removes all poison effects from target.\n"
        "Expert+: also grants temporary poison resistance.\n"
        "Expert: 25% / 5 min. Master: 50% / 5 min. GM: 75% / 10 min.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Cure Poison implementation pending — needs poison named effect "
            "removal, DamageResistanceMixin poison resistance buff at "
            "EXPERT+ tiers."
        )

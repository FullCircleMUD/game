"""
Cure Blindness — divine healing spell, available from BASIC mastery.

Removes the BLINDED condition from a target. At higher tiers, also
cures DEAFENED.

Scaling:
    BASIC(1):   Cures BLINDED,              mana 4
    SKILLED(2): Cures BLINDED,              mana 6
    EXPERT(3):  Cures BLINDED + DEAFENED,   mana 8
    MASTER(4):  Cures BLINDED + DEAFENED,   mana 10
    GM(5):      Cures BLINDED + DEAFENED,   mana 12

No cooldown. Instant effect.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class CureBlindness(Spell):
    key = "cure_blindness"
    aliases = ["cureblind", "cb"]
    name = "Cure Blindness"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 12}
    target_type = "friendly"
    cooldown = 0
    description = "Removes blindness and deafness through divine healing."
    mechanics = (
        "Removes BLINDED condition from target.\n"
        "Expert+: also removes DEAFENED.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Cure Blindness implementation pending — needs BLINDED/DEAFENED "
            "condition removal, tier check for DEAFENED at EXPERT+."
        )

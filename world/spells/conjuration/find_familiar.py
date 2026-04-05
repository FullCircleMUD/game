"""
Find Familiar — conjuration spell, available from BASIC mastery.

Summons a small magical familiar that follows the caster. The
familiar is non-combat — it serves as a companion, scout, and
utility pet.

Scaling:
    BASIC(1):   Cat/owl/rat, follows caster,           mana 8
    SKILLED(2): + can send to adjacent room to scout,   mana 12
    EXPERT(3):  + see through familiar's eyes,          mana 16
    MASTER(4):  + familiar can carry 1 small item,      mana 20
    GM(5):      + familiar persists across sessions,    mana 25

Only one familiar at a time. Recasting dismisses the old one.
Familiar vanishes if caster dies or dismisses it.
Duration: 1 hour (Basic) to permanent (GM).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class FindFamiliar(Spell):
    key = "find_familiar"
    aliases = ["familiar", "ff"]
    name = "Find Familiar"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 8, 2: 12, 3: 16, 4: 20, 5: 25}
    target_type = "none"
    cooldown = 0
    description = "Summons a small magical familiar to serve as a companion."
    mechanics = (
        "Summons a non-combat familiar (cat, owl, or rat).\n"
        "Basic: follows caster. Skilled: scout adjacent rooms.\n"
        "Expert: see through its eyes. Master: carry 1 small item.\n"
        "GM: persists across sessions.\n"
        "Only one at a time. Recasting dismisses the old one.\n"
        "Duration: 1 hour (Basic) to permanent (GM)."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Find Familiar implementation pending — needs pet/companion "
            "system, familiar NPC typeclass, follow behaviour, dismiss "
            "mechanic, scout/see-through at higher tiers."
        )

"""
Divine Aegis — divine protection spell, available from GRANDMASTER mastery.

Grants total damage immunity to a friendly target for a short duration.
Thematic parallel to Abjuration's Invulnerability spell.

Scaling:
    GM(5): mana TBD, short duration

Cooldown: 3 rounds (default GM).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DivineAegis(Spell):
    key = "divine_aegis"
    aliases = ["da"]
    name = "Divine Aegis"
    school = skills.DIVINE_PROTECTION
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "friendly"
    description = "Envelops the target in an impenetrable divine shield."
    mechanics = (
        "Total damage immunity on target for a short duration.\n"
        "Thematic parallel to Abjuration's Invulnerability.\n"
        "3 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Divine Aegis implementation pending — needs damage immunity "
            "mechanic (hook in take_damage or via named effect)."
        )

"""
Death Ward — divine healing spell, available from GRANDMASTER mastery.

Preemptive buff cast on a friendly target. When the target would die
(HP reaches 0), the effect intercepts the death mechanic: HP is set to 1,
the Death Ward effect is consumed, and the target survives.

This hooks into take_damage() / die() to intercept lethal damage.
The named effect is consumed on trigger (one-time protection).

Scaling:
    GM(5): mana TBD

Cooldown: 3 rounds (default GM).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DeathWard(Spell):
    key = "death_ward"
    aliases = ["dw"]
    name = "Death Ward"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "friendly"
    description = "Places a divine ward on the target that intercepts a killing blow."
    mechanics = (
        "Preemptive buff — cast on self or ally.\n"
        "When the warded target would die, they survive on 1 HP instead.\n"
        "The ward is consumed on trigger (one-time protection).\n"
        "3 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Death Ward implementation pending — needs hook in "
            "take_damage()/die() to check for death_ward named effect "
            "and intercept lethal damage."
        )

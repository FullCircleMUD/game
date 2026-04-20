"""
Phantasmal Killer — illusion spell, available from GRANDMASTER mastery.

The trophy illusion spell. Creates an illusion so real the target
believes it completely — a phantasmal manifestation of their deepest
fear. Contested save: failure means massive psychic damage or instant
death for low-HP targets.

Scaling:
    GM(5): 100 mana, contested WIS save

Damage on failed save: 20d6 psychic damage. If target HP drops to 0,
they die from fright (special death message).

On successful save: half damage (10d6).

Cooldown: 1 round.

DEPENDENCY: Needs WIS save mechanic, psychic damage type, and
contested save system.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class PhantasmalKiller(Spell):
    key = "phantasmal_killer"
    aliases = ["pk"]
    name = "Phantasmal Killer"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Conjures a phantasm of the target's deepest fear that can kill outright."
    mechanics = (
        "Contested WIS save. On failure: 20d6 psychic damage.\n"
        "If target reaches 0 HP, they die from fright.\n"
        "On successful save: half damage (10d6).\n"
        "100 mana. 1 round cooldown."
    )

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Contested WIS save: caster d20 + WIS mod vs target d20 + WIS mod
        #      → Alternatively: target WIS save vs caster's spell DC
        #   2. On failed save: roll 20d6 psychic damage
        #      → apply_spell_damage(target, raw, DamageType.PSYCHIC)
        #      → if target HP reaches 0: special death ("dies of fright")
        #   3. On successful save: half damage (10d6)
        #   4. Return multi-perspective messages
        #
        # Needs:
        #   - WIS save mechanic / spell DC
        #   - DamageType.PSYCHIC
        #   - Special death message for fright kills
        raise NotImplementedError(
            "Phantasmal Killer implementation pending — needs WIS save "
            "mechanic and DamageType.PSYCHIC."
        )

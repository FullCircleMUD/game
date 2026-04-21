"""
Cone of Cold — evocation spell, available from MASTER mastery.

Blasts a cone of freezing cold at enemies in the room. Safe AoE — only
hits enemies, never the caster or allies.

The primary target is resolved by name ("cast cone of cold goblin") and
is a guaranteed hit. The AoE framework builds the secondaries list —
enemies only at the primary target's height. Each secondary has a
diminishing chance to be caught in the cone:

    Primary target: guaranteed hit
    1st secondary:  80% chance to hit
    2nd secondary:  60% chance to hit
    3rd secondary:  40% chance to hit
    4th+:           20% chance to hit

All enemies hit are also SLOWED (shorter than Frostbolt — AoE tax):
    MASTER(4): 1 round
    GM(5):     2 rounds

Damage scales with mastery tier (big spell scaling: +3d6/tier):
    MASTER(4): 10d6 cold  (avg 35, mana 35)
    GM(5):     13d6 cold  (avg 46, mana 46)

Cooldown: 2 rounds (default MASTER).
"""

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


# Diminishing hit chance for secondaries: 80%, 60%, 40%, 20%...
# Primary target is guaranteed hit (not in this table).
_SECONDARY_HIT_CHANCES = [80, 60, 40]  # 4th+ defaults to 20


def _get_secondary_hit_chance(index):
    """Return hit chance percentage for the Nth secondary (0-indexed)."""
    if index < len(_SECONDARY_HIT_CHANCES):
        return _SECONDARY_HIT_CHANCES[index]
    return 20


@register_spell
class ConeOfCold(Spell):
    key = "cone_of_cold"
    aliases = ["coc"]
    name = "Cone of Cold"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.MASTER
    mana_cost = {4: 35, 5: 46}
    target_type = "actor_hostile"
    aoe = "safe"
    description = "Blasts a cone of freezing cold at enemies, slowing those it hits."
    mechanics = (
        "Safe AoE — only hits enemies, never you or allies.\n"
        "Primary target: guaranteed hit.\n"
        "Diminishing accuracy on secondaries: 80%, 60%, 40%, 20%+.\n"
        "All enemies hit are SLOWED: 1 round (Master), 2 rounds (GM).\n"
        "Damage: 10d6 (Master), 13d6 (Grandmaster) cold.\n"
        "2 round cooldown."
    )

    # Dice per tier: base 10d6 at MASTER, +3d6 per tier above
    _DICE = {4: 10, 5: 13}
    # SLOWED duration — shorter than Frostbolt because AoE
    _SLOW_ROUNDS = {4: 1, 5: 2}

    def _execute(self, caster, target, **kwargs):
        secondaries = kwargs.get("secondaries", [])
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 10)
        raw_damage = dice.roll(f"{num_dice}d6")
        rounds = self._SLOW_ROUNDS.get(tier, 1)

        # Primary target: guaranteed hit
        hit_targets = []
        missed_targets = []

        actual = apply_spell_damage(target, raw_damage, DamageType.COLD, caster=caster)
        hit_targets.append((target, actual))
        target.apply_slowed(rounds, source=caster)
        target.msg(
            f"|C{caster.key}'s cone of cold blasts you for "
            f"{actual} cold damage!|n"
        )

        # Secondaries: diminishing hit chance per index
        for i, enemy in enumerate(secondaries):
            chance = _get_secondary_hit_chance(i)
            roll = dice.roll("1d100")
            if roll <= chance:
                actual = apply_spell_damage(enemy, raw_damage, DamageType.COLD, caster=caster)
                hit_targets.append((enemy, actual))
                enemy.apply_slowed(rounds, source=caster)
                enemy.msg(
                    f"|C{caster.key}'s cone of cold blasts you for "
                    f"{actual} cold damage!|n"
                )
            else:
                missed_targets.append(enemy)

        # Build caster summary
        hit_parts = [f"{e.key} ({d})" for e, d in hit_targets]
        hit_summary = ", ".join(hit_parts) if hit_parts else "no one"

        if missed_targets:
            miss_names = ", ".join(e.key for e in missed_targets)
            first_msg = (
                f"|CYou blast a cone of freezing cold! "
                f"It hits {hit_summary} and slows them! "
                f"{miss_names} dodged the blast.|n"
            )
        else:
            first_msg = (
                f"|CYou blast a cone of freezing cold! "
                f"It hits {hit_summary} and slows them!|n"
            )

        return (True, {
            "first": first_msg,
            "second": None,
            "third": (
                f"|C{caster.key} unleashes a devastating cone of "
                f"freezing cold!|n"
            ),
        })

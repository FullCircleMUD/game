"""
Flame Burst — evocation spell, available from SKILLED mastery.

Ignites a burst of flame around the caster, scorching nearby enemies.
Safe AoE — only hits enemies, never the caster or allies.

The primary target is resolved by name ("cast flame burst goblin") and
is a guaranteed hit. The AoE framework builds the secondaries list —
enemies only at the primary target's height. Each secondary has a
diminishing chance to be caught in the burst:

    Primary target: guaranteed hit
    1st secondary:  80% chance to hit
    2nd secondary:  60% chance to hit
    3rd secondary:  40% chance to hit
    4th+:           20% chance to hit

Damage scales with mastery tier (+1d6/tier):
    SKILLED(2): 3d6 fire  (avg 11, mana 11)
    EXPERT(3):  4d6 fire  (avg 14, mana 14)
    MASTER(4):  5d6 fire  (avg 18, mana 18)
    GM(5):      6d6 fire  (avg 21, mana 21)

Cooldown: 0 (default SKILLED).
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
class FlameBurst(Spell):
    key = "flame_burst"
    aliases = ["flb"]
    name = "Flame Burst"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 11, 3: 14, 4: 18, 5: 21}
    target_type = "actor_hostile"
    aoe = "safe"
    description = "Ignites a burst of flame around the caster, scorching nearby enemies."
    mechanics = (
        "Safe AoE — only hits enemies, never you or allies.\n"
        "Primary target: guaranteed hit.\n"
        "Diminishing accuracy on secondaries: 80%, 60%, 40%, 20%+.\n"
        "Damage: 3d6 (Skilled), 4d6 (Expert), "
        "5d6 (Master), 6d6 (Grandmaster) fire.\n"
        "No cooldown."
    )

    # Dice per tier: 3d6 at SKILLED, +1d6 per tier
    _DICE = {2: 3, 3: 4, 4: 5, 5: 6}

    def _execute(self, caster, target, **kwargs):
        secondaries = kwargs.get("secondaries", [])
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 2)
        raw_damage = dice.roll(f"{num_dice}d6")

        # Primary target: guaranteed hit
        hit_targets = []
        missed_targets = []

        actual = apply_spell_damage(target, raw_damage, DamageType.FIRE)
        hit_targets.append((target, actual))
        target.msg(
            f"|r{caster.key}'s flame burst scorches you for "
            f"{actual} fire damage!|n"
        )

        # Secondaries: diminishing hit chance per index
        for i, enemy in enumerate(secondaries):
            chance = _get_secondary_hit_chance(i)
            roll = dice.roll("1d100")
            if roll <= chance:
                actual = apply_spell_damage(enemy, raw_damage, DamageType.FIRE)
                hit_targets.append((enemy, actual))
                enemy.msg(
                    f"|r{caster.key}'s flame burst scorches you for "
                    f"{actual} fire damage!|n"
                )
            else:
                missed_targets.append(enemy)

        # Build caster summary
        hit_parts = [f"{e.key} ({d})" for e, d in hit_targets]
        hit_summary = ", ".join(hit_parts) if hit_parts else "no one"

        if missed_targets:
            miss_names = ", ".join(e.key for e in missed_targets)
            first_msg = (
                f"|rYou ignite a burst of flame! "
                f"It scorches {hit_summary}! "
                f"{miss_names} avoided the blast.|n"
            )
        else:
            first_msg = (
                f"|rYou ignite a burst of flame! "
                f"It scorches {hit_summary}!|n"
            )

        return (True, {
            "first": first_msg,
            "second": None,
            "third": (
                f"|r{caster.key} ignites a burst of flame that "
                f"scorches the area!|n"
            ),
        })

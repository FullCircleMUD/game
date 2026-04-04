"""
Cone of Cold — evocation spell, available from MASTER mastery.

Blasts a cone of freezing cold at enemies in the room. Safe AoE — only
hits enemies, never the caster or allies. However, the more enemies in
the room, the harder it is to catch them all in the cone:

    1st enemy: 100% chance to hit
    2nd enemy:  80% chance to hit
    3rd enemy:  60% chance to hit
    4th enemy:  40% chance to hit
    5th+:       20% chance to hit

All enemies hit are also SLOWED (shorter than Frostbolt — AoE tax):
    MASTER(4): 2 rounds
    GM(5):     3 rounds

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
from world.spells.spell_utils import apply_spell_damage, get_room_enemies


# Diminishing hit chance for safe AoE: 100%, 80%, 60%, 40%, 20%...
_HIT_CHANCES = [100, 80, 60, 40]  # 5th+ defaults to 20


def _get_hit_chance(index):
    """Return hit chance percentage for the Nth enemy (0-indexed)."""
    if index < len(_HIT_CHANCES):
        return _HIT_CHANCES[index]
    return 20


@register_spell
class ConeOfCold(Spell):
    key = "cone_of_cold"
    aliases = ["coc"]
    name = "Cone of Cold"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.MASTER
    mana_cost = {4: 35, 5: 46}
    target_type = "none"
    description = "Blasts a cone of freezing cold at enemies, slowing those it hits."
    mechanics = (
        "Safe AoE — only hits enemies, never you or allies.\n"
        "Diminishing accuracy: 1st enemy 100%, 2nd 80%, 3rd 60%, 4th 40%, 5th+ 20%.\n"
        "All enemies hit are SLOWED: 2 rounds (Master), 3 rounds (GM).\n"
        "Damage: 10d6 (Master), 13d6 (Grandmaster) cold.\n"
        "2 round cooldown."
    )

    # Dice per tier: base 10d6 at MASTER, +3d6 per tier above
    _DICE = {4: 10, 5: 13}
    # SLOWED duration — shorter than Frostbolt because AoE
    # also SLOWED is auto applied here. no contested roll...
    _SLOW_ROUNDS = {4: 1, 5: 2}

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 10)
        raw_damage = dice.roll(f"{num_dice}d6")

        enemies = get_room_enemies(caster)
        if not enemies:
            return (True, {
                "first": "You blast a cone of freezing cold but there are no enemies to hit!",
                "second": None,
                "third": (
                    f"{caster.key} blasts a cone of freezing cold, "
                    f"but it hits nothing!"
                ),
            })

        # Roll hit chance for each enemy
        hit_targets = []
        missed_targets = []
        for i, enemy in enumerate(enemies):
            chance = _get_hit_chance(i)
            roll = dice.roll("1d100")
            if roll <= chance:
                hit_targets.append(enemy)
            else:
                missed_targets.append(enemy)

        # Apply damage and SLOWED to all hit targets
        damage_results = []
        for enemy in hit_targets:
            actual = apply_spell_damage(enemy, raw_damage, DamageType.COLD)
            damage_results.append((enemy, actual))
            # Apply SLOWED via named effect
            rounds = self._SLOW_ROUNDS.get(tier, 2)
            enemy.apply_slowed(rounds, source=caster)
            enemy.msg(
                f"|C{caster.key}'s cone of cold blasts you for "
                f"{actual} cold damage!|n"
            )

        # Build caster summary
        hit_parts = [f"{e.key} ({d})" for e, d in damage_results]
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

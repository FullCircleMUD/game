"""
Flame Burst — evocation spell, available from SKILLED mastery.

Ignites a burst of flame around the caster, scorching nearby enemies.
Safe AoE — only hits enemies, never the caster or allies. The more
enemies in the room, the harder it is to catch them all in the burst:

    1st enemy: 100% chance to hit
    2nd enemy:  80% chance to hit
    3rd enemy:  60% chance to hit
    4th enemy:  40% chance to hit
    5th+:       20% chance to hit

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
from world.spells.spell_utils import apply_spell_damage, get_room_enemies


# Diminishing hit chance for safe AoE: 100%, 80%, 60%, 40%, 20%...
_HIT_CHANCES = [100, 80, 60, 40]  # 5th+ defaults to 20


def _get_hit_chance(index):
    """Return hit chance percentage for the Nth enemy (0-indexed)."""
    if index < len(_HIT_CHANCES):
        return _HIT_CHANCES[index]
    return 20


@register_spell
class FlameBurst(Spell):
    key = "flame_burst"
    aliases = ["burst"]
    name = "Flame Burst"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 11, 3: 14, 4: 18, 5: 21}
    target_type = "none"
    description = "Ignites a burst of flame around the caster, scorching nearby enemies."
    mechanics = (
        "Safe AoE — only hits enemies, never you or allies.\n"
        "Diminishing accuracy: 1st enemy 100%, 2nd 80%, 3rd 60%, 4th 40%, 5th+ 20%.\n"
        "Damage: 3d6 (Skilled), 4d6 (Expert), "
        "5d6 (Master), 6d6 (Grandmaster) fire.\n"
        "No cooldown."
    )

    # Dice per tier: 3d6 at SKILLED, +1d6 per tier
    _DICE = {2: 3, 3: 4, 4: 5, 5: 6}

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 2)
        raw_damage = dice.roll(f"{num_dice}d6")

        enemies = get_room_enemies(caster)
        if not enemies:
            return (True, {
                "first": "You ignite a burst of flame but there are no enemies to hit!",
                "second": None,
                "third": (
                    f"{caster.key} ignites a burst of flame, "
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

        # Apply damage to all hit targets
        damage_results = []
        for enemy in hit_targets:
            actual = apply_spell_damage(enemy, raw_damage, DamageType.FIRE)
            damage_results.append((enemy, actual))
            enemy.msg(
                f"|r{caster.key}'s flame burst scorches you for "
                f"{actual} fire damage!|n"
            )

        # Build caster summary
        hit_parts = [f"{e.key} ({d})" for e, d in damage_results]
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

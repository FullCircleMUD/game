"""
Drain Life — necromancy spell, available from BASIC mastery.

The necromancer's workhorse spell. Deals cold damage to a single target
and heals the caster for 100% of the damage dealt. Cannot exceed max HP.

The necro's Magic Missile — cheap, spammable, and defines the class
fantasy. At high tiers, a necro with a big mana pool becomes a drain
tank: trading mana for immortality one cast at a time.

Damage scales with mastery tier (starter scaling: +1d6/tier):
    BASIC(1):   2d6 cold  (avg  7, mana  5)
    SKILLED(2): 3d6 cold  (avg 11, mana  8)
    EXPERT(3):  4d6 cold  (avg 14, mana 10)
    MASTER(4):  5d6 cold  (avg 18, mana 14)
    GM(5):      6d6 cold  (avg 21, mana 16)

Heal = 100% of actual damage dealt (after resistance). The necro feels
like a vampire — every hit feeds them. Balance comes from counterplay:
    - Cold-resistant mobs reduce both damage AND healing
    - SILENCED/STUNNED stops casting entirely
    - Antimagic Field strips everything
    - Single-target only — can't heal through multiple attackers
    - Mana runs out eventually

Cooldown: 0 (same as Magic Missile — spammable workhorse).
"""

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


@register_spell
class DrainLife(Spell):
    key = "drain_life"
    aliases = ["dl", "drain"]
    name = "Drain Life"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "hostile"
    cooldown = 0
    description = "Drains the life force from a target, healing yourself."
    mechanics = (
        "Deals cold damage to a single target and heals you for 100% of damage dealt.\n"
        "Cannot exceed your maximum HP.\n"
        "Damage: 2d6 (Basic) to 6d6 (Grandmaster) cold.\n"
        "Cold resistance reduces both damage AND healing.\n"
        "No cooldown."
    )

    # Dice per tier: base 2d6, +1d6 per tier (starter scaling)
    _DICE = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6}

    def _execute(self, caster, target):
        # Undead have no life force to drain
        if target.tags.get("undead", category="creature_type"):
            return (False, {
                "first": (
                    f"|rYour dark magic finds no life force to drain "
                    f"from {target.key}!|n"
                ),
                "second": None,
                "third": (
                    f"|r{caster.key} reaches toward {target.key} with "
                    f"dark energy, but it dissipates harmlessly.|n"
                ),
            })

        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 2)
        raw_damage = dice.roll(f"{num_dice}d6")

        # Apply damage (with resistance check)
        actual_damage = apply_spell_damage(target, raw_damage, DamageType.COLD)

        # Heal caster for 100% of actual damage dealt, capped at max HP
        heal_amount = min(actual_damage, caster.hp_max - caster.hp)
        caster.hp = min(caster.hp_max, caster.hp + actual_damage)

        if heal_amount > 0:
            heal_msg = f" and drain |g{heal_amount}|n HP"
        else:
            heal_msg = ""

        return (True, {
            "first": (
                f"|rYou drain the life from {target.key}, dealing "
                f"{actual_damage} cold damage{heal_msg}!|n"
            ),
            "second": (
                f"|r{caster.key} drains your life force, dealing "
                f"{actual_damage} cold damage!|n"
            ),
            "third": (
                f"|r{caster.key} drains the life from {target.key}, "
                f"dealing {actual_damage} cold damage!|n"
            ),
        })

"""
Drain Life — necromancy spell, available from BASIC mastery.

The necromancer's workhorse spell. Deals cold damage to a single target
and heals the caster for 100% of the damage dealt. Cannot exceed max HP.

The necro's answer to Magic Missile — same baseline damage envelope as
the other BASIC workhorses, but every hit feeds the caster. At high
tiers, a necro with a big mana pool becomes a drain tank: trading mana
for immortality one cast at a time.

Damage scales with mastery tier — matches the cluster-baseline budget
of (1d4+1) per tier; the heal is the distinguishing rider:
    BASIC(1):   1×(1d4+1) cold  (avg  3.5, mana  5)
    SKILLED(2): 2×(1d4+1) cold  (avg  7.0, mana  8)
    EXPERT(3):  3×(1d4+1) cold  (avg 10.5, mana 10)
    MASTER(4):  4×(1d4+1) cold  (avg 14.0, mana 14)
    GM(5):      5×(1d4+1) cold  (avg 17.5, mana 16)

Heal = 100% of actual damage dealt (after resistance), capped at
effective_hp_max. The necro feels like a vampire — every hit feeds them. Balance comes from counterplay:
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
    aliases = ["dl"]
    name = "Drain Life"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Drains the life force from a target, healing yourself."
    mechanics = (
        "Deals cold damage to a single target and heals you for 100% of damage dealt.\n"
        "Cannot exceed your effective maximum HP.\n"
        "Damage: tier × (1d4+1) cold — 1d4+1 (Basic) to 5×(1d4+1) (Grandmaster).\n"
        "Cold resistance reduces both damage AND healing.\n"
        "No cooldown."
    )

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
        # tier × (1d4+1) — matches the BASIC workhorse damage cluster; the
        # heal is the rider that distinguishes this spell from Magic Missile.
        raw_damage = sum(dice.roll("1d4+1") for _ in range(tier))

        # Apply damage (with resistance check)
        actual_damage = apply_spell_damage(target, raw_damage, DamageType.COLD, caster=caster)

        # Heal caster for 100% of actual damage dealt, capped at max HP.
        # Use effective_hp_max so the CON-modifier portion of max HP isn't
        # clipped off (hp_max is pre-CON; a full-HP caster can sit above it).
        hp_max = caster.effective_hp_max
        heal_amount = min(actual_damage, hp_max - caster.hp)
        caster.hp = min(hp_max, caster.hp + actual_damage)

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

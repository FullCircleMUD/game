"""
Frostbolt — evocation spell, available from BASIC mastery.

Single-target cold debuff spell. The value is in the SLOWED effect,
not the damage. Damage is flat 1d6 cold at all tiers. SLOWED duration
scales with mastery (1–5 rounds).

SLOWED requires a contested check:
    Caster: d20 + INT modifier + mastery bonus
    Target: d20 + CON modifier
    Caster must beat target to apply SLOWED.

SLOWED mechanic (enforced in combat_handler):
    - Caps attacks at 1 per round (main hand only)
    - Blocks off-hand attacks entirely
    - Per-round sluggish message

Duration scaling:
    BASIC(1):   1 round,  mana 5
    SKILLED(2): 2 rounds, mana 8
    EXPERT(3):  3 rounds, mana 10
    MASTER(4):  4 rounds, mana 14
    GM(5):      5 rounds, mana 16

Cooldown: 0 (spammable workhorse, same tier as Magic Missile).
"""

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


@register_spell
class Frostbolt(Spell):
    key = "frostbolt"
    aliases = ["frb"]
    name = "Frostbolt"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Hurls a bolt of searing cold that slows the target."
    mechanics = (
        "Single-target cold spell — value is in the debuff.\n"
        "Damage: 1d6 cold (flat, all tiers).\n"
        "Contested check to apply SLOWED:\n"
        "  Caster d20 + INT mod + mastery bonus vs Target d20 + CON mod.\n"
        "Duration: 1 round (Basic) to 5 rounds (Grandmaster).\n"
        "SLOWED caps attacks at 1/round and blocks off-hand.\n"
        "No cooldown."
    )

    # SLOWED duration = tier
    _SLOW_ROUNDS = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # --- Flat 1d6 cold damage ---
        raw_damage = dice.roll("1d6")
        actual_damage = apply_spell_damage(target, raw_damage, DamageType.COLD)

        # --- Contested check for SLOWED ---
        caster_roll = dice.roll("1d20")
        caster_int = caster.get_attribute_bonus(caster.intelligence)
        mastery_bonus = MasteryLevel(tier).bonus
        caster_total = caster_roll + caster_int + mastery_bonus

        target_roll = dice.roll("1d20")
        target_con = target.get_attribute_bonus(target.constitution)
        target_total = target_roll + target_con

        slowed = False
        rounds = self._SLOW_ROUNDS.get(tier, 1)
        if caster_total > target_total:
            applied = target.apply_slowed(rounds, source=caster)
            slowed = applied

        # --- Build messages ---
        s = "s" if rounds != 1 else ""
        if slowed:
            first_msg = (
                f"|CYou hurl a frostbolt at {target.key}, dealing "
                f"{actual_damage} cold damage!\n"
                f"*SLOWED* The cold seeps into their limbs! "
                f"({rounds} round{s})|n"
            )
        else:
            first_msg = (
                f"|CYou hurl a frostbolt at {target.key}, dealing "
                f"{actual_damage} cold damage!\n"
                f"{target.key} resists the slowing cold.|n"
            )

        second_msg = (
            f"|C{caster.key} hurls a frostbolt at you, dealing "
            f"{actual_damage} cold damage!|n"
        )

        third_msg = (
            f"|C{caster.key} hurls a frostbolt at {target.key}!|n"
        )

        return (True, {
            "first": first_msg,
            "second": second_msg,
            "third": third_msg,
        })

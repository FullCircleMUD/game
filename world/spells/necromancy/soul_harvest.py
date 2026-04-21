"""
Soul Harvest — necromancy spell, available from EXPERT mastery.

Unleashes a wave of necrotic energy that drains life from everything
at the primary target's height, except the caster and undead creatures.

The primary target is resolved by name ("cast soul harvest goblin"). The
AoE framework builds the secondaries list — everyone at the target's
height except the caster (unsafe_self). Undead creatures are filtered
out in _execute (they have no life force to drain).

Each target gets a CON save — success means zero damage (the target's
body holds onto its life force). Failure means full necrotic damage.
The caster heals for the total damage dealt across all targets who
failed the save.

Damage scales with mastery tier (big spell scaling: +3d6/tier):
    EXPERT(3):  8d6 necrotic  (avg 28, mana 28)
    MASTER(4): 11d6 necrotic  (avg 39, mana 39)
    GM(5):     14d6 necrotic  (avg 49, mana 49)

Cooldown: 1 round (default EXPERT).
"""

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


@register_spell
class SoulHarvest(Spell):
    key = "soul_harvest"
    aliases = ["sh"]
    name = "Soul Harvest"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "actor_hostile"
    aoe = "unsafe_self"
    description = (
        "Unleashes a wave of necrotic energy that drains life from "
        "everything nearby, healing the caster. Undead are immune."
    )
    mechanics = (
        "Unsafe AoE (caster excluded) — hits enemies AND allies.\n"
        "Undead creatures are immune (no life force to drain).\n"
        "CON save for no damage (DC = caster d20 + INT + mastery).\n"
        "Caster heals for total damage dealt to targets who failed the save.\n"
        "Damage: 8d6 (Expert), 11d6 (Master), 14d6 (Grandmaster) necrotic.\n"
        "1 round cooldown."
    )

    # Dice per tier: base 8d6 at EXPERT, +3d6 per tier above
    _DICE = {3: 8, 4: 11, 5: 14}

    def _execute(self, caster, target, **kwargs):
        secondaries = kwargs.get("secondaries", [])
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 8)
        raw_damage = dice.roll(f"{num_dice}d6")

        # Save DC: caster d20 + INT + mastery
        save_dc_roll = dice.roll("1d20")
        caster_int = caster.get_attribute_bonus(caster.intelligence)
        mastery_bonus = MasteryLevel(tier).bonus
        save_dc = save_dc_roll + caster_int + mastery_bonus

        # All targets = primary + secondaries, filter out undead
        all_targets = [
            e for e in [target] + secondaries
            if not e.tags.get("undead", category="creature_type")
        ]

        if not all_targets:
            return (True, {
                "first": (
                    "You unleash a wave of necrotic energy but there's "
                    "nothing to drain!"
                ),
                "second": None,
                "third": (
                    f"{caster.key} unleashes a wave of dark energy "
                    f"that dissipates harmlessly."
                ),
            })

        # Apply damage to targets who fail the CON save
        total_drained = 0
        damage_results = []
        saved_targets = []
        for entity in all_targets:
            # CON save for no damage
            save_roll = dice.roll("1d20")
            con_bonus = entity.get_attribute_bonus(entity.constitution)
            save_total = save_roll + con_bonus
            saved = save_total >= save_dc

            if saved:
                saved_targets.append(entity)
                entity.msg(
                    f"|W{caster.key}'s necrotic wave washes over you "
                    f"but your body resists the drain.|n"
                )
            else:
                actual = apply_spell_damage(
                    entity, raw_damage, DamageType.NECROTIC, caster=caster,
                )
                total_drained += actual
                damage_results.append((entity, actual))
                entity.msg(
                    f"|r{caster.key}'s soul harvest drains you for "
                    f"{actual} necrotic damage!|n"
                )

        # Heal caster for total drained, capped at max HP.
        # Use effective_hp_max so the CON-modifier portion of max HP isn't
        # clipped off (hp_max is pre-CON; a full-HP caster can sit above it).
        hp_max = caster.effective_hp_max
        heal_amount = min(total_drained, hp_max - caster.hp)
        caster.hp = min(hp_max, caster.hp + total_drained)

        # Build caster summary
        parts = [f"{e.key} ({d})" for e, d in damage_results]
        target_summary = ", ".join(parts) if parts else "no one"

        save_info = f"(Save DC {save_dc})"
        if saved_targets:
            save_names = ", ".join(e.key for e in saved_targets)
            save_msg = f" {save_names} resisted."
        else:
            save_msg = ""

        if heal_amount > 0:
            heal_msg = f" You drain |g{heal_amount}|n HP from their life force!"
        else:
            heal_msg = " You are already at full health."

        return (True, {
            "first": (
                f"|rYou unleash a wave of necrotic energy! "
                f"It drains {target_summary}.{save_msg}{heal_msg}\n"
                f"{save_info}|n"
            ),
            "second": None,
            "third": (
                f"|r{caster.key} unleashes a terrible wave of dark energy "
                f"that drains the life from everything nearby!|n"
            ),
        })

"""
Fireball — evocation spell, available from EXPERT mastery.

Hurls a massive ball of fire that explodes, hitting everything in the room
at the same level. Unsafe AoE — damages enemies, allies, AND the caster.

Each target gets a DEX save for half damage. Save DC = caster d20 + INT
bonus + mastery bonus.

Damage scales with mastery tier (big spell scaling: +3d6/tier):
    EXPERT(3):  8d6 fire  (avg 28, mana 28)
    MASTER(4): 11d6 fire  (avg 39, mana 39)
    GM(5):     14d6 fire  (avg 49, mana 49)

Cooldown: 1 round (default EXPERT).
"""

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage, get_room_all


@register_spell
class Fireball(Spell):
    key = "fireball"
    aliases = ["fb"]
    name = "Fireball"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    description = "Hurls a massive ball of fire that explodes, engulfing everything in flames."
    mechanics = (
        "Unsafe AoE — hits EVERYTHING in the room including you and your allies.\n"
        "DEX save for half damage (DC = caster d20 + INT + mastery).\n"
        "Safe to cast at range (flying vs ground, or across area rooms).\n"
        "Damage: 8d6 (Expert), 11d6 (Master), 14d6 (Grandmaster) fire.\n"
        "Fire resistance reduces damage; vulnerability increases it.\n"
        "1 round cooldown."
    )

    # Dice per tier: base 8d6 at EXPERT, +3d6 per tier above
    _DICE = {3: 8, 4: 11, 5: 14}

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 8)
        raw_damage = dice.roll(f"{num_dice}d6")

        # Save DC: caster d20 + INT + mastery
        save_dc_roll = dice.roll("1d20")
        caster_int = caster.get_attribute_bonus(caster.intelligence)
        mastery_bonus = MasteryLevel(tier).bonus
        save_dc = save_dc_roll + caster_int + mastery_bonus

        targets = get_room_all(caster)
        if not targets:
            return (True, {
                "first": "You hurl a fireball but there's nothing to hit!",
                "second": None,
                "third": "A fireball explodes harmlessly!",
            })

        # Apply damage to every entity in the room (including caster)
        damage_results = []
        for entity in targets:
            # DEX save for half damage
            save_roll = dice.roll("1d20")
            dex_bonus = entity.get_attribute_bonus(entity.dexterity)
            save_total = save_roll + dex_bonus
            saved = save_total >= save_dc

            damage = raw_damage // 2 if saved else raw_damage
            actual = apply_spell_damage(entity, damage, DamageType.FIRE)
            damage_results.append((entity, actual, saved))
            # Send individual damage message to each target (except caster)
            if entity != caster:
                half = " (saved — half damage)" if saved else ""
                entity.msg(
                    f"|r{caster.key}'s fireball engulfs you for "
                    f"{actual} fire damage!{half}|n"
                )

        # Build caster summary
        parts = []
        caster_damage = 0
        caster_saved = False
        for entity, dmg, saved in damage_results:
            half_tag = "½" if saved else ""
            if entity == caster:
                caster_damage = dmg
                caster_saved = saved
            else:
                parts.append(f"{entity.key} ({dmg}{half_tag})")

        target_summary = ", ".join(parts) if parts else "no one else"
        save_info = f"(Save DC {save_dc})"
        if caster_damage:
            half = " (half)" if caster_saved else ""
            first_msg = (
                f"|rYou hurl a massive fireball! It hits {target_summary} "
                f"and burns you for {caster_damage}{half} fire damage!\n"
                f"{save_info}|n"
            )
        else:
            first_msg = (
                f"|rYou hurl a massive fireball! It hits {target_summary}!\n"
                f"{save_info}|n"
            )

        return (True, {
            "first": first_msg,
            "second": None,
            "third": (
                f"|r{caster.key} hurls a massive fireball that engulfs "
                f"everything in flames!|n"
            ),
        })

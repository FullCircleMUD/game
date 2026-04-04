"""
Call Lightning — nature magic spell, available from EXPERT mastery.

Calls down a lightning storm that strikes everything in the room.
Unsafe AoE — damages enemies, allies, AND the caster. The druid's
Fireball equivalent, but weaker damage (nature school trades damage
for CC via Entangle).

Each target gets a DEX save for half damage. Save DC = caster d20 + WIS
bonus + mastery bonus.

Damage scales with mastery tier (big spell scaling: +3d6/tier):
    EXPERT(3):  6d6 lightning  (avg 21, mana 21)
    MASTER(4):  9d6 lightning  (avg 32, mana 32)
    GM(5):     12d6 lightning  (avg 42, mana 42)

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
class CallLightning(Spell):
    key = "call_lightning"
    aliases = ["cl"]
    name = "Call Lightning"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 21, 4: 32, 5: 42}
    target_type = "none"
    description = "Calls down a devastating lightning storm that strikes everything in the room."
    mechanics = (
        "Unsafe AoE — hits EVERYTHING in the room including you and your allies.\n"
        "DEX save for half damage (DC = caster d20 + WIS + mastery).\n"
        "Safe to cast at range (flying vs ground, or across area rooms).\n"
        "Damage: 6d6 (Expert), 9d6 (Master), 12d6 (Grandmaster) lightning.\n"
        "Lightning resistance reduces damage; vulnerability increases it.\n"
        "1 round cooldown."
    )

    # Dice per tier: base 6d6 at EXPERT, +3d6 per tier above
    _DICE = {3: 6, 4: 9, 5: 12}

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        num_dice = self._DICE.get(tier, 6)
        raw_damage = dice.roll(f"{num_dice}d6")

        # Save DC: caster d20 + WIS + mastery
        save_dc_roll = dice.roll("1d20")
        caster_wis = caster.get_attribute_bonus(caster.wisdom)
        mastery_bonus = MasteryLevel(tier).bonus
        save_dc = save_dc_roll + caster_wis + mastery_bonus

        targets = get_room_all(caster)
        if not targets:
            return (True, {
                "first": (
                    "|WYou call down lightning but there's nothing to hit!|n"
                ),
                "second": None,
                "third": "|WLightning crashes down harmlessly!|n",
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
            actual = apply_spell_damage(
                entity, damage, DamageType.LIGHTNING,
            )
            damage_results.append((entity, actual, saved))
            # Send individual damage message to each target (except caster)
            if entity != caster:
                half = " (saved — half damage)" if saved else ""
                entity.msg(
                    f"|W{caster.key}'s lightning storm strikes you for "
                    f"{actual} lightning damage!{half}|n"
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
                f"|WYou call down a raging lightning storm! Bolts strike "
                f"{target_summary} and shock you for {caster_damage}{half} "
                f"lightning damage!\n{save_info}|n"
            )
        else:
            first_msg = (
                f"|WYou call down a raging lightning storm! Bolts strike "
                f"{target_summary}!\n{save_info}|n"
            )

        return (True, {
            "first": first_msg,
            "second": None,
            "third": (
                f"|W{caster.key} calls down a raging lightning storm that "
                f"strikes everything in the room!|n"
            ),
        })

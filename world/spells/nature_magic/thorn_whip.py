"""
Thorn Whip — nature magic spell, available from BASIC mastery.

Lashes a target with a thorny vine, dealing piercing damage and
pulling them to the caster's height/depth. The target is held at
that position for N rounds, unable to change height.

When the hold expires, physics takes over — if they're airborne
without FLY they fall (fall damage), if they're underwater without
WATER_BREATHING the breath timer starts.

Scaling:
    BASIC(1):   1d6 piercing, hold 1 round,  mana 3
    SKILLED(2): 2d6 piercing, hold 2 rounds, mana 5
    EXPERT(3):  3d6 piercing, hold 3 rounds, mana 7
    MASTER(4):  4d6 piercing, hold 4 rounds, mana 9
    GM(5):      5d6 piercing, hold 5 rounds, mana 12

Contested WIS (caster) vs STR (target) for the pull.
Damage always applies regardless of contest result.
HUGE+ immune to pull (damage still applies).
"""

from enums.size import Size
from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.named_effect import NamedEffect
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


_IMMUNE_SIZES = frozenset({Size.HUGE, Size.GARGANTUAN})


@register_spell
class ThornWhip(Spell):
    key = "thorn_whip"
    aliases = ["twhip", "tw"]
    name = "Thorn Whip"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Lashes a target with a thorny vine, pulling them to your level."
    mechanics = (
        "Deals (tier)d6 piercing damage (always, even on failed pull).\n"
        "Contested WIS vs STR — on win, pulls target to caster's height.\n"
        "Target held at that height for 1-5 rounds (mastery-scaled).\n"
        "On hold expiry: fall damage if airborne without FLY, drowning if underwater.\n"
        "HUGE+ immune to pull. Damage always applies.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # Damage always applies
        raw_damage = dice.roll(f"{tier}d6")
        actual_damage = apply_spell_damage(target, raw_damage, DamageType.PIERCING)

        # Size gate for pull
        target_size = getattr(target, "size", None)
        size_immune = target_size and target_size in _IMMUNE_SIZES

        pulled = False
        hold_rounds = tier
        caster_height = caster.room_vertical_position
        target_height = target.room_vertical_position

        if not size_immune and caster_height != target_height:
            # Contested WIS (caster) vs STR (target)
            caster_roll = dice.roll("1d20")
            caster_wis = caster.get_attribute_bonus(caster.wisdom)
            mastery_bonus = MasteryLevel(tier).bonus
            caster_total = caster_roll + caster_wis + mastery_bonus

            target_roll = dice.roll("1d20")
            target_str = target.get_attribute_bonus(
                getattr(target, "strength", 10)
            )
            target_total = target_roll + target_str

            if caster_total > target_total:
                # Pull target to caster's height
                target.room_vertical_position = caster_height
                pulled = True

                # Apply hold effect
                target.apply_named_effect(
                    NamedEffect.THORN_WHIP_HELD,
                    duration=hold_rounds,
                )

        # Build messages
        s = "s" if hold_rounds != 1 else ""
        if pulled:
            if caster_height == 0:
                pull_desc = "dragging them to the ground"
            elif caster_height > 0:
                pull_desc = f"dragging them into the air (height {caster_height})"
            else:
                pull_desc = f"dragging them underwater (depth {caster_height})"

            first_msg = (
                f"|GYou lash {target.key} with a thorny vine, "
                f"{pull_desc}!\n"
                f"|r{actual_damage}|G piercing damage! "
                f"*HELD* ({hold_rounds} round{s})|n"
            )
            second_msg = (
                f"|G{caster.key} lashes you with a thorny vine, "
                f"dragging you to their level!\n"
                f"|r{actual_damage}|G piercing damage!|n"
            )
            third_msg = (
                f"|G{caster.key} lashes {target.key} with a thorny vine, "
                f"{pull_desc}! |r{actual_damage}|G piercing damage!|n"
            )
        else:
            if size_immune:
                extra = f" {target.key} is too large to pull!"
            elif caster_height == target_height:
                extra = ""
            else:
                extra = f" The vine fails to pull {target.key}!"

            first_msg = (
                f"|GYou lash {target.key} with a thorny vine! "
                f"|r{actual_damage}|G piercing damage!{extra}|n"
            )
            second_msg = (
                f"|G{caster.key} lashes you with a thorny vine! "
                f"|r{actual_damage}|G piercing damage!|n"
            )
            third_msg = (
                f"|G{caster.key} lashes {target.key} with a thorny vine! "
                f"|r{actual_damage}|G piercing damage!|n"
            )

        return (True, {
            "first": first_msg,
            "second": second_msg,
            "third": third_msg,
        })

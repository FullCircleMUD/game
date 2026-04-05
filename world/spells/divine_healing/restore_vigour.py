"""
Vigorise — divine_healing spell, available from BASIC mastery.

Restores movement points to a target (self or ally). Generous scaling:
    (tier + 4)d6 + wisdom modifier

BASIC: 5d6 + wis_mod, SKILLED: 6d6 + wis_mod, ... GM: 9d6 + wis_mod
"""

from utils.dice_roller import dice
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Vigorise(Spell):
    key = "vigorise"
    aliases = ["vigorize", "vig"]
    name = "Vigorise"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 12, 4: 16, 5: 20}
    target_type = "friendly"
    spell_range = "melee"
    description = "Channels divine energy to restore stamina and vigour."
    mechanics = (
        "Restores movement points to a single target (self if no target specified).\n"
        "Restoration: (tier + 4)d6 + Wisdom modifier.\n"
        "Scales: 5d6 (Basic) to 9d6 (Grandmaster) + WIS mod.\n"
        "Cannot exceed target's maximum movement.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        move_max = target.move_max

        # Refuse if target is already at full movement — refund mana
        if target.move >= move_max:
            tier = self.get_caster_tier(caster)
            caster.mana += self.mana_cost.get(tier, 0)
            name = "You" if target == caster else target.key
            verb = "don't" if target == caster else "doesn't"
            return (False, f"{name} {verb} need rest.")

        tier = self.get_caster_tier(caster)
        num_dice = tier + 4  # BASIC(1): 5d6, SKILLED(2): 6d6, ... GM(5): 9d6
        restore_roll = dice.roll(f"{num_dice}d6")
        wis_bonus = caster.get_attribute_bonus(caster.wisdom)
        total_restore = max(0, restore_roll + wis_bonus)

        # Clamp to not exceed max movement
        actual = max(0, min(total_restore, move_max - target.move))
        target.move = min(move_max, target.move + actual)

        if target == caster:
            return (True, {
                "first": f"You feel a surge of energy as |g{actual}|n movement is restored.",
                "second": None,
                "third": f"{caster.key} glows briefly with divine energy.",
            })
        return (True, {
            "first": f"You restore |g{actual}|n movement to {target.key}.",
            "second": f"{caster.key} restores |g{actual}|n movement to you.",
            "third": f"{caster.key} vigorises {target.key} with divine energy.",
        })

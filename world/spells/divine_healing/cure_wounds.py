"""
Cure Wounds — divine_healing spell, available from BASIC mastery.

Heals a target (self or ally). Scales linearly:
    tier d6 + wisdom modifier (applied once)

BASIC: 1d6 + wis_mod, SKILLED: 2d6 + wis_mod, ... GM: 5d6 + wis_mod
"""

from utils.dice_roller import dice
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class CureWounds(Spell):
    key = "cure_wounds"
    name = "Cure Wounds"
    school = skills.DIVINE_HEALING
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 12, 4: 16, 5: 20}
    target_type = "friendly"
    spell_range = "melee"
    description = "Channels divine energy to mend wounds on yourself or an ally."
    mechanics = (
        "Heals a single target (self if no target specified).\n"
        "Healing: (tier)d6 + Wisdom modifier.\n"
        "Scales: 1d6 (Basic) to 5d6 (Grandmaster) + WIS mod.\n"
        "Cannot exceed target's maximum HP.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        heal_roll = dice.roll(f"{tier}d6")
        wis_bonus = caster.get_attribute_bonus(caster.wisdom)
        total_heal = max(0, heal_roll + wis_bonus)

        # Clamp to not exceed max HP
        actual = min(total_heal, target.hp_max - target.hp)
        target.hp = min(target.hp_max, target.hp + total_heal)

        if target == caster:
            return (True, {
                "first": f"You heal yourself for |g{actual}|n hit points.",
                "second": None,
                "third": f"{caster.key} heals themselves for |g{actual}|n hit points.",
            })
        return (True, {
            "first": f"You heal {target.key} for |g{actual}|n hit points.",
            "second": f"{caster.key} heals you for |g{actual}|n hit points.",
            "third": f"{caster.key} heals {target.key} for |g{actual}|n hit points.",
        })

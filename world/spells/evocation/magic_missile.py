"""
Magic Missile — evocation spell, available from BASIC mastery.

Fires glowing darts of force that auto-hit the target.
Scales with mastery tier: 1 missile at BASIC, up to 5 at GRANDMASTER.
Each missile deals 1d4+2 force damage.
"""

from utils.dice_roller import dice
from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.spell_utils import apply_spell_damage
from world.spells.registry import register_spell


@register_spell
class MagicMissile(Spell):
    key = "magic_missile"
    aliases = ["mm"]
    name = "Magic Missile"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "actor_hostile"
    description = "Fires glowing darts of magical force that unerringly strike the target."
    mechanics = (
        "Auto-hit — no attack roll needed.\n"
        "Fires one missile per mastery tier (1 at Basic, 5 at Grandmaster).\n"
        "Each missile deals 1d4+2 force damage.\n"
        "Works at melee and ranged distance.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        missiles = tier  # 1 at BASIC(1), 2 at SKILLED(2), ... 5 at GM(5)
        total_damage = 0
        for _ in range(missiles):
            total_damage += dice.roll("1d4+2")

        total_damage = apply_spell_damage(target, total_damage, DamageType.FORCE, caster=caster)

        s = "s" if missiles > 1 else ""
        return (True, {
            "first": (
                f"You fire {missiles} glowing missile{s} at {target.key}, "
                f"dealing |r{total_damage}|n force damage!"
            ),
            "second": (
                f"{caster.key} fires {missiles} glowing missile{s} at you, "
                f"dealing |r{total_damage}|n force damage!"
            ),
            "third": (
                f"{caster.key} fires {missiles} glowing missile{s} at {target.key}, "
                f"dealing |r{total_damage}|n force damage!"
            ),
        })

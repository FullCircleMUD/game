"""
Fire Bolt — evocation spell, available from BASIC mastery.

Hurls a single bolt of fire at a target. Unlike Magic Missile, this
requires a hit roll (d20 + INT mod + mastery bonus vs target AC)
but deals higher damage per tier.

Scaling (single bolt, must hit):
    BASIC(1):   1d8 fire,  mana 3
    SKILLED(2): 2d8 fire,  mana 5
    EXPERT(3):  3d8 fire,  mana 7
    MASTER(4):  4d8 fire,  mana 9
    GM(5):      5d8 fire,  mana 12

Hit roll: d20 + INT modifier + mastery bonus vs target AC.
Can miss, can crit (nat 20 doubles damage dice).
Fire damage type — subject to fire resistance/vulnerability.
No cooldown.
"""

from enums.damage_type import DamageType
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell
from world.spells.spell_utils import apply_spell_damage


@register_spell
class FireBolt(Spell):
    key = "fire_bolt"
    aliases = ["fbolt", "fb"]
    name = "Fire Bolt"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 3, 2: 5, 3: 7, 4: 9, 5: 12}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Hurls a bolt of fire at a target."
    mechanics = (
        "Single bolt — requires hit roll (d20 + INT mod + mastery bonus vs AC).\n"
        "Damage: 1d8 (Basic) to 5d8 (GM) fire.\n"
        "Can miss. Nat 20 crits (double damage dice).\n"
        "Fire damage — subject to resistance/vulnerability.\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)
        mastery_bonus = MasteryLevel(tier).bonus
        int_mod = caster.get_attribute_bonus(caster.intelligence)

        # Hit roll
        d20 = dice.roll("1d20")
        is_crit = d20 == 20
        total_hit = d20 + int_mod + mastery_bonus
        target_ac = target.effective_ac

        if total_hit < target_ac and not is_crit:
            # Miss
            return (True, {
                "first": (
                    f"You hurl a bolt of fire at {target.key}, "
                    f"but it streaks past harmlessly!"
                ),
                "second": (
                    f"{caster.key} hurls a bolt of fire at you, "
                    f"but it streaks past harmlessly!"
                ),
                "third": (
                    f"{caster.key} hurls a bolt of fire at {target.key}, "
                    f"but it streaks past harmlessly!"
                ),
            })

        # Hit — roll damage
        num_dice = tier * 2 if is_crit else tier
        raw_damage = dice.roll(f"{num_dice}d8")
        actual_damage = apply_spell_damage(target, raw_damage, DamageType.FIRE)

        crit_str = " |r*CRITICAL*|n" if is_crit else ""
        return (True, {
            "first": (
                f"You hurl a bolt of fire at {target.key}!{crit_str} "
                f"|r{actual_damage}|n fire damage!"
            ),
            "second": (
                f"{caster.key} hurls a bolt of fire at you!{crit_str} "
                f"|r{actual_damage}|n fire damage!"
            ),
            "third": (
                f"{caster.key} hurls a bolt of fire at {target.key}!{crit_str} "
                f"|r{actual_damage}|n fire damage!"
            ),
        })

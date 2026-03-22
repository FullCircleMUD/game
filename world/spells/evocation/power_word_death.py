"""
Power Word: Death — evocation capstone, GRANDMASTER only.

The ultimate single-target finisher. Point at something and it dies.

Mechanic (two-tiered):
    1. Target at or below HP_THRESHOLD (20):
       - Roll d20. Nat 1 = fails. Anything else = instant death.
    2. Target above HP_THRESHOLD:
       - Contested save:
         Caster:  d20 + INT mod + mastery bonus (+8 at GM)
         Target:  d20 + CON mod + 1 per 5 HD above threshold
       - Nat 20 from caster = always kills
       - Nat 1 from caster = always fails
       - Caster wins or ties = target dies
       - Target wins = nothing happens (no damage, no partial effect)

Mana: 100 (flat — doesn't follow damage formula since there's no damage roll).
Cooldown: 3 rounds (default GM).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


HP_THRESHOLD = 20


@register_spell
class PowerWordDeath(Spell):
    key = "power_word_death"
    aliases = ["pwd", "wod"]
    name = "Power Word: Death"
    school = skills.EVOCATION
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "hostile"
    description = "Speaks a single word of absolute power. The target dies."
    mechanics = (
        "Single target — instant kill, no damage roll.\n"
        "Target at or below 20 HP: auto-kill (unless you roll nat 1).\n"
        "Target above 20 HP: contested save —\n"
        "  You: d20 + INT mod + mastery bonus (+8)\n"
        "  Target: d20 + CON mod + 1 per 5 HP above 20\n"
        "  Tie or win = target dies. Lose = nothing happens.\n"
        "Nat 20 always kills. Nat 1 always fails.\n"
        "Costs 100 mana. 3 round cooldown."
    )

    def _execute(self, caster, target):
        caster_roll = dice.roll("1d20")

        # --- Nat 1 always fails ---
        if caster_roll == 1:
            return (True, {
                "first": (
                    f"|YYou speak the Word of Death at {target.key}... "
                    f"but the magic fizzles! |r(Nat 1)|n"
                ),
                "second": (
                    f"|Y{caster.key} speaks a terrible word of power at you... "
                    f"but nothing happens!|n"
                ),
                "third": (
                    f"|Y{caster.key} speaks a terrible word of power at "
                    f"{target.key}... but the magic fizzles!|n"
                ),
            })

        # --- Target at or below threshold: instant kill (unless nat 1) ---
        if getattr(target, "hp", 0) <= HP_THRESHOLD:
            _kill_target(target)
            return (True, {
                "first": (
                    f"|R|*You speak the Word of Death. {target.key} "
                    f"crumples lifelessly to the ground!|n"
                ),
                "second": (
                    f"|R|*{caster.key} speaks a terrible word of power. "
                    f"Darkness engulfs you!|n"
                ),
                "third": (
                    f"|R|*{caster.key} speaks a terrible word of power. "
                    f"{target.key} crumples lifelessly to the ground!|n"
                ),
            })

        # --- Above threshold: contested save ---
        # Nat 20 always kills
        if caster_roll == 20:
            _kill_target(target)
            return (True, {
                "first": (
                    f"|R|*You speak the Word of Death at {target.key}! "
                    f"The word resonates with absolute power! |y(Nat 20)|n "
                    f"|R|*{target.key} crumples lifelessly to the ground!|n"
                ),
                "second": (
                    f"|R|*{caster.key} speaks a terrible word of power. "
                    f"Darkness engulfs you!|n"
                ),
                "third": (
                    f"|R|*{caster.key} speaks a terrible word of power "
                    f"with absolute authority! {target.key} crumples "
                    f"lifelessly to the ground!|n"
                ),
            })

        # Full contested roll
        int_mod = _ability_mod(getattr(caster, "intelligence", 10))
        mastery_bonus = MasteryLevel.GRANDMASTER.bonus  # +8
        caster_total = caster_roll + int_mod + mastery_bonus

        target_roll = dice.roll("1d20")
        con_mod = _ability_mod(getattr(target, "constitution", 10))
        hd_over = max(0, getattr(target, "hp", 0) - HP_THRESHOLD)
        hd_bonus = hd_over // 5
        target_total = target_roll + con_mod + hd_bonus

        # Caster wins or ties = kill
        if caster_total >= target_total:
            _kill_target(target)
            return (True, {
                "first": (
                    f"|R|*You speak the Word of Death at {target.key}! "
                    f"(d20:{caster_roll}+{int_mod}+{mastery_bonus}={caster_total} "
                    f"vs {target_roll}+{con_mod}+{hd_bonus}={target_total}) "
                    f"{target.key} crumples lifelessly to the ground!|n"
                ),
                "second": (
                    f"|R|*{caster.key} speaks a terrible word of power. "
                    f"Darkness engulfs you!|n"
                ),
                "third": (
                    f"|R|*{caster.key} speaks a terrible word of power! "
                    f"{target.key} crumples lifelessly to the ground!|n"
                ),
            })

        # Target wins = spell fails
        return (True, {
            "first": (
                f"|YYou speak the Word of Death at {target.key}... "
                f"(d20:{caster_roll}+{int_mod}+{mastery_bonus}={caster_total} "
                f"vs {target_roll}+{con_mod}+{hd_bonus}={target_total}) "
                f"{target.key} resists the killing word!|n"
            ),
            "second": (
                f"|Y{caster.key} speaks a terrible word of power at you... "
                f"but you resist!|n"
            ),
            "third": (
                f"|Y{caster.key} speaks a terrible word of power at "
                f"{target.key}... but {target.key} resists!|n"
            ),
        })


def _ability_mod(score):
    """D&D-style ability modifier: floor((score - 10) / 2)."""
    return (score - 10) // 2


def _kill_target(target):
    """Set HP to 0 and trigger death."""
    target.hp = 0
    if hasattr(target, "die"):
        target.die("combat")

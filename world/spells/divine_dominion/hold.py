"""
Hold — divine dominion spell, available from EXPERT mastery.

Binds a target in divine chains, paralyzing them. The target gets a
WIS save each round to break free. Caster's full contested total
(d20 + WIS + mastery) sets the save DC for the life of the spell.

Size gate scales with mastery:
    EXPERT(3): up to MEDIUM,  3 rounds, mana 28
    MASTER(4): up to LARGE,   4 rounds, mana 39
    GM(5):     up to HUGE,    5 rounds, mana 49

GARGANTUAN always immune.
Cooldown: 1 round (default EXPERT).
"""

from enums.actor_size import ActorSize
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from combat.combat_utils import get_actor_size
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell

# Per-tier size immunity: sizes the spell CANNOT affect at each tier
_HOLD_IMMUNE = {
    3: {ActorSize.LARGE, ActorSize.HUGE, ActorSize.GARGANTUAN},
    4: {ActorSize.HUGE, ActorSize.GARGANTUAN},
    5: {ActorSize.GARGANTUAN},
}

# Duration in rounds per tier
_HOLD_ROUNDS = {3: 3, 4: 4, 5: 5}

# Human-readable size cap per tier (for messaging)
_SIZE_CAP_NAMES = {3: "medium", 4: "large", 5: "huge"}


@register_spell
class Hold(Spell):
    key = "hold"
    aliases = ["hp"]
    name = "Hold"
    school = skills.DIVINE_DOMINION
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "actor_hostile"
    description = "Binds the target in divine chains, paralyzing them."
    mechanics = (
        "Single target — PARALYSED with per-round WIS save to break free.\n"
        "Caster rolls d20 + WIS + mastery to set the save DC.\n"
        "Target rolls d20 + WIS each round to escape.\n"
        "Size gate: EXPERT = medium, MASTER = large, GM = huge.\n"
        "Duration: 3/4/5 rounds. 1 round cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # --- Size gate ---
        immune_sizes = _HOLD_IMMUNE.get(tier, {ActorSize.GARGANTUAN})
        target_size = get_actor_size(target)
        if target_size in immune_sizes:
            cap_name = _SIZE_CAP_NAMES.get(tier, "medium")
            return (True, {
                "first": (
                    f"|Y{target.key} is too powerful to hold! "
                    f"Your divine authority can only bind creatures "
                    f"up to {cap_name} size.|n"
                ),
                "second": (
                    f"|Y{caster.key} attempts to bind you in divine chains, "
                    f"but your sheer presence shatters them!|n"
                ),
                "third": (
                    f"|Y{caster.key} attempts to bind {target.key} in "
                    f"divine chains, but the creature is too powerful!|n"
                ),
            })

        # --- Contested WIS vs WIS check ---
        caster_roll = dice.roll("1d20")
        caster_wis = caster.get_attribute_bonus(caster.wisdom)
        mastery_bonus = MasteryLevel(tier).bonus
        caster_total = caster_roll + caster_wis + mastery_bonus

        target_roll = dice.roll("1d20")
        target_wis = target.get_attribute_bonus(target.wisdom)
        target_total = target_roll + target_wis

        caster_bonus_display = caster_wis + mastery_bonus
        contest_detail = (
            f"(Will: {caster_roll} + {caster_bonus_display} = "
            f"{caster_total} vs {target_total})"
        )

        # --- Contested check failed ---
        if caster_total <= target_total:
            return (True, {
                "first": (
                    f"|YYou attempt to bind {target.key} in divine chains, "
                    f"but they resist your authority!\n"
                    f"{contest_detail}|n"
                ),
                "second": (
                    f"|Y{caster.key} attempts to bind you in divine chains, "
                    f"but you shake off the compulsion!|n"
                ),
                "third": (
                    f"|Y{caster.key} attempts to bind {target.key} in "
                    f"divine chains, but they resist!|n"
                ),
            })

        # --- Apply PARALYSED with per-round WIS save ---
        rounds = _HOLD_ROUNDS.get(tier, 3)
        applied = target.apply_paralysed(
            rounds, source=caster,
            save_dc=caster_total,
            save_stat="wisdom",
            save_messages={
                "success": (
                    "|gYou strain against the divine chains and break free! "
                    "(rolled {roll} vs DC {dc})|n"
                ),
                "fail": (
                    "|rYou struggle against the divine chains but cannot "
                    "break free! (rolled {roll} vs DC {dc})|n"
                ),
                "success_third": (
                    "{name} strains against the divine chains and breaks free!"
                ),
                "fail_third": (
                    "{name} struggles against the divine chains but cannot "
                    "break free!"
                ),
            },
            messages={
                "start": (
                    "Glowing divine chains wrap around you, "
                    "binding you in place!"
                ),
                "end": "The divine chains shatter and release you!",
                "start_third": (
                    "Glowing divine chains wrap around {name}, "
                    "binding them in place!"
                ),
                "end_third": (
                    "The divine chains binding {name} shatter "
                    "and release them!"
                ),
            },
        )

        s = "s" if rounds != 1 else ""
        if applied:
            first = (
                f"|Y*HOLD* You bind {target.key} in glowing divine chains! "
                f"They cannot move!\n"
                f"*PARALYSED* ({rounds} round{s}, save DC {caster_total})\n"
                f"{contest_detail}|n"
            )
        else:
            first = (
                f"|YYou attempt to bind {target.key} in divine chains, "
                f"but they are already paralysed!\n"
                f"{contest_detail}|n"
            )

        return (True, {
            "first": first,
            "second": (
                f"|Y{caster.key} speaks with divine authority — "
                f"glowing chains wrap around you, binding you in place!|n"
            ),
            "third": (
                f"|Y{caster.key} binds {target.key} in glowing divine "
                f"chains — they freeze in place!|n"
            ),
        })

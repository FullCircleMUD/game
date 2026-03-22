"""
Entangle — nature magic spell, available from BASIC mastery.

Summons grasping vines that root a target in place. The druid/ranger's
bread-and-butter CC spell.

Contested check to apply ENTANGLED:
    Caster: d20 + WIS modifier + mastery bonus
    Target: d20 + STR modifier  (strong creatures resist vines)
    Caster must beat target to apply ENTANGLED.

ENTANGLED mechanic (enforced in combat_handler):
    - Skips target's action entirely (same as stunned/prone/paralysed)
    - Grants advantage to all enemies attacking the entangled target

Duration scaling:
    BASIC(1):   1 round,  mana 5
    SKILLED(2): 2 rounds, mana 8
    EXPERT(3):  3 rounds, mana 10
    MASTER(4):  4 rounds, mana 14
    GM(5):      5 rounds, mana 16

Cooldown: 0 (spammable workhorse).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Entangle(Spell):
    key = "entangle"
    aliases = ["ent"]
    name = "Entangle"
    school = skills.NATURE_MAGIC
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 8, 3: 10, 4: 14, 5: 16}
    target_type = "hostile"
    cooldown = 0
    description = "Summons grasping vines that root the target in place."
    mechanics = (
        "Single-target nature CC — roots target with vines.\n"
        "Contested check: caster d20 + WIS + mastery vs target d20 + STR.\n"
        "On success: ENTANGLED — target cannot act, attackers gain advantage.\n"
        "Duration: 1 round (Basic) to 5 rounds (Grandmaster).\n"
        "No cooldown."
    )

    # Duration = tier in rounds
    _ENTANGLE_ROUNDS = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # --- Contested check for ENTANGLED ---
        caster_roll = dice.roll("1d20")
        caster_wis = caster.get_attribute_bonus(caster.wisdom)
        mastery_bonus = MasteryLevel(tier).bonus
        caster_total = caster_roll + caster_wis + mastery_bonus

        target_roll = dice.roll("1d20")
        target_str = target.get_attribute_bonus(target.strength)
        target_total = target_roll + target_str

        caster_bonus_display = caster_wis + mastery_bonus
        contest_detail = (
            f"(Vines: {caster_roll} + {caster_bonus_display} = "
            f"{caster_total} vs {target_total})"
        )

        entangled = False
        rounds = self._ENTANGLE_ROUNDS.get(tier, 1)
        if caster_total > target_total:
            applied = target.apply_entangled(
                rounds, source=caster, save_dc=caster_total,
                messages={
                    "start": (
                        "Thick vines burst from the ground, "
                        "wrapping around your legs and binding you in place!"
                    ),
                    "end": "The vines wither and crumble, releasing you!",
                    "start_third": (
                        "Thick vines burst from the ground, "
                        "wrapping around {name}'s legs and binding them in place!"
                    ),
                    "end_third": (
                        "The vines binding {name} wither and crumble, "
                        "releasing them!"
                    ),
                },
            )
            entangled = applied

        # --- Build messages ---
        s = "s" if rounds != 1 else ""
        if entangled:
            first_msg = (
                f"|GYou call upon nature's wrath! Grasping vines erupt "
                f"from the ground and bind {target.key}!\n"
                f"*ENTANGLED* ({rounds} round{s})\n"
                f"{contest_detail}|n"
            )
        else:
            first_msg = (
                f"|GYou call upon nature's wrath, but {target.key} "
                f"tears free of the grasping vines!\n"
                f"{contest_detail}|n"
            )

        second_msg = (
            f"|G{caster.key} calls upon nature's wrath — grasping vines "
            f"erupt from the ground around you!|n"
        )

        third_msg = (
            f"|G{caster.key} calls upon nature's wrath — grasping vines "
            f"erupt around {target.key}!|n"
        )

        return (True, {
            "first": first_msg,
            "second": second_msg,
            "third": third_msg,
        })

"""
Blindness — divine dominion spell, available from BASIC mastery.

Inflicts BLINDED on a single target, giving them disadvantage on all
attack rolls. Contested WIS (caster) vs CON (target) save.

Scaling (duration):
    BASIC(1):   3 rounds,  mana 5
    SKILLED(2): 4 rounds,  mana 7
    EXPERT(3):  5 rounds,  mana 9
    MASTER(4):  6 rounds,  mana 12
    GM(5):      8 rounds,  mana 15

Contested WIS (caster) vs CON (target). HUGE+ immune.
Save-each-round (CON) to break early.
"""

from enums.actor_size import ActorSize
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


_DURATION_ROUNDS = {1: 3, 2: 4, 3: 5, 4: 6, 5: 8}

# HUGE and larger are immune
_IMMUNE_SIZES = frozenset({ActorSize.HUGE, ActorSize.GARGANTUAN})


@register_spell
class Blindness(Spell):
    key = "blindness"
    aliases = ["blind"]
    name = "Blindness"
    school = skills.DIVINE_DOMINION
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 5, 2: 7, 3: 9, 4: 12, 5: 15}
    target_type = "hostile"
    cooldown = 0
    description = "Strikes a creature blind with divine authority."
    mechanics = (
        "Inflicts BLINDED — disadvantage on all attack rolls.\n"
        "Contested WIS vs CON. Save-each-round (CON) to break early.\n"
        "HUGE+ immune.\n"
        "Duration: 3 rounds (Basic) to 8 rounds (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # Size gate
        target_size = getattr(target, "size", None)
        if target_size and target_size in _IMMUNE_SIZES:
            return (True, {
                "first": (
                    f"|W{target.key} is too large to be affected by "
                    f"your blindness spell!|n"
                ),
                "second": (
                    f"|W{caster.key} tries to blind you, but you are "
                    f"too powerful to be affected!|n"
                ),
                "third": (
                    f"|W{caster.key} tries to blind {target.key}, but "
                    f"the creature is too large to be affected!|n"
                ),
            })

        # Contested WIS (caster) vs CON (target)
        caster_roll = dice.roll("1d20")
        caster_wis = caster.get_attribute_bonus(caster.wisdom)
        mastery_bonus = MasteryLevel(tier).bonus
        caster_total = caster_roll + caster_wis + mastery_bonus

        target_roll = dice.roll("1d20")
        target_con = target.get_attribute_bonus(
            getattr(target, "constitution", 10)
        )
        target_total = target_roll + target_con

        caster_bonus_display = caster_wis + mastery_bonus
        contest_detail = (
            f"(WIS: {caster_roll} + {caster_bonus_display} = "
            f"{caster_total} vs CON: {target_total})"
        )

        rounds = _DURATION_ROUNDS.get(tier, 3)
        blinded = False

        if caster_total > target_total:
            applied = target.apply_blinded(
                rounds, source=caster, save_dc=caster_total,
                save_messages={
                    "save_success": (
                        "You blink hard and your vision clears! "
                        "(CON save: {{roll}} vs DC {{dc}})"
                    ),
                    "save_fail": (
                        "You struggle to see but the darkness holds! "
                        "(CON save: {{roll}} vs DC {{dc}})"
                    ),
                    "save_success_third": (
                        "{{name}} blinks hard and their vision clears!"
                    ),
                    "save_fail_third": (
                        "{{name}} struggles to see but remains blinded!"
                    ),
                },
                messages={
                    "start": (
                        "Divine authority strikes your eyes! "
                        "Darkness fills your vision!"
                    ),
                    "end": "Your vision gradually returns.",
                    "start_third": (
                        "Divine authority strikes {name}'s eyes! "
                        "They stumble, blinded!"
                    ),
                    "end_third": (
                        "{name}'s vision clears and they can see again."
                    ),
                },
            )
            blinded = applied

        s = "s" if rounds != 1 else ""
        if blinded:
            first_msg = (
                f"|WYou invoke divine authority upon {target.key}! "
                f"Darkness fills their eyes!\n"
                f"*BLINDED* ({rounds} round{s})\n"
                f"{contest_detail}|n"
            )
        else:
            first_msg = (
                f"|WYou invoke divine authority upon {target.key}, "
                f"but they resist the blindness!\n"
                f"{contest_detail}|n"
            )

        second_msg = (
            f"|W{caster.key} invokes divine authority — darkness "
            f"closes around your eyes!|n"
        )
        third_msg = (
            f"|W{caster.key} invokes divine authority upon "
            f"{target.key}!|n"
        )

        return (True, {
            "first": first_msg,
            "second": second_msg,
            "third": third_msg,
        })

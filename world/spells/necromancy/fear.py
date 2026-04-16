"""
Fear — necromancy spell, available from BASIC mastery.

Inflicts FRIGHTENED on a single target, causing them to flee in
terror each combat round. Contested INT+mastery (caster) vs WIS
(target) to set the DC. Save-each-round WIS to break free.

Scaling (duration = max rounds before auto-expire):
    BASIC(1):   1 round,  mana 4
    SKILLED(2): 2 rounds, mana 6
    EXPERT(3):  3 rounds, mana 8
    MASTER(4):  4 rounds, mana 10
    GM(5):      5 rounds, mana 14

FRIGHTENED: target attempts to flee through a random exit each round.
If no exits, they cower (lose action). HUGE+ immune.
"""

from enums.actor_size import ActorSize
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


_DURATION_ROUNDS = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

# HUGE and larger are immune
_IMMUNE_SIZES = frozenset({ActorSize.HUGE, ActorSize.GARGANTUAN})


@register_spell
class Fear(Spell):
    key = "fear"
    aliases = ["scare"]
    name = "Fear"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.BASIC
    mana_cost = {1: 4, 2: 6, 3: 8, 4: 10, 5: 14}
    target_type = "actor_hostile"
    cooldown = 0
    description = "Fills a creature with supernatural terror, causing it to flee."
    mechanics = (
        "Inflicts FRIGHTENED — target flees through a random exit each round.\n"
        "Contested INT+mastery vs WIS. Save-each-round WIS to break early.\n"
        "HUGE+ immune. If no exits, target cowers (loses action).\n"
        "Duration: 1 round (Basic) to 5 rounds (GM).\n"
        "No cooldown."
    )

    def _execute(self, caster, target):
        tier = self.get_caster_tier(caster)

        # Size gate
        target_size = getattr(target, "size", None)
        if target_size and target_size in _IMMUNE_SIZES:
            return (True, {
                "first": (
                    f"|r{target.key} is too large to be frightened!|n"
                ),
                "second": (
                    f"|r{caster.key} tries to frighten you, but you are "
                    f"too powerful to be affected!|n"
                ),
                "third": (
                    f"|r{caster.key} tries to frighten {target.key}, but "
                    f"the creature is too large to be affected!|n"
                ),
            })

        # Contested INT+mastery (caster) vs WIS (target)
        caster_roll = dice.roll("1d20")
        caster_int = caster.get_attribute_bonus(caster.intelligence)
        mastery_bonus = MasteryLevel(tier).bonus
        caster_total = caster_roll + caster_int + mastery_bonus

        target_roll = dice.roll("1d20")
        target_wis = target.get_attribute_bonus(
            getattr(target, "wisdom", 10)
        )
        target_total = target_roll + target_wis

        caster_bonus_display = caster_int + mastery_bonus
        contest_detail = (
            f"(INT: {caster_roll} + {caster_bonus_display} = "
            f"{caster_total} vs WIS: {target_total})"
        )

        rounds = _DURATION_ROUNDS.get(tier, 1)
        frightened = False

        if caster_total > target_total:
            applied = target.apply_frightened(
                rounds, source=caster, save_dc=caster_total,
                save_messages={
                    "success": (
                        "You steel your nerves and shake off the terror! "
                        "(WIS save: {roll} vs DC {dc})"
                    ),
                    "fail": (
                        "You try to resist but the terror holds you! "
                        "(WIS save: {roll} vs DC {dc})"
                    ),
                    "success_third": (
                        "{name} steels their nerves and shakes off the terror!"
                    ),
                    "fail_third": (
                        "{name} whimpers, still gripped by supernatural fear!"
                    ),
                },
                messages={
                    "start": (
                        "Supernatural terror grips you! You must flee!"
                    ),
                    "end": (
                        "The supernatural terror fades and you regain "
                        "your courage."
                    ),
                    "start_third": (
                        "{name} is gripped by supernatural terror and "
                        "tries to flee!"
                    ),
                    "end_third": (
                        "{name} shakes off the supernatural terror and "
                        "stands firm."
                    ),
                },
            )
            frightened = applied

        s = "s" if rounds != 1 else ""
        if frightened:
            first_msg = (
                f"|rYou channel dark energy at {target.key}! "
                f"Supernatural terror grips them!\n"
                f"*FRIGHTENED* ({rounds} round{s})\n"
                f"{contest_detail}|n"
            )
        else:
            first_msg = (
                f"|rYou channel dark energy at {target.key}, "
                f"but they resist the terror!\n"
                f"{contest_detail}|n"
            )

        second_msg = (
            f"|r{caster.key} channels dark energy toward you — "
            f"a wave of supernatural terror washes over you!|n"
        )
        third_msg = (
            f"|r{caster.key} channels dark energy at {target.key}!|n"
        )

        return (True, {
            "first": first_msg,
            "second": second_msg,
            "third": third_msg,
        })

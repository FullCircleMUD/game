"""
Mass Confusion — illusion spell, available from EXPERT mastery.

The "Fireball of illusion" — ALL entities in the room (unsafe,
caster INCLUDED) have their minds shattered. Confused entities
attack randomly — they can't tell friend from foe.

Uses the CONFUSED condition. Combat tick checks for CONFUSED and
overrides target selection with a random entity in the room.

Foresight charges auto-save against confusion (when implemented).

Scaling:
    EXPERT(3):  1 round duration, mana 28
    MASTER(4):  2 rounds,         mana 39
    GM(5):      3 rounds,         mana 49

Mana cost matches Fireball at each tier.

Cooldown: 1 round (default EXPERT).

DEPENDENCY: Needs CONFUSED condition check in combat tick for
random target selection, and Foresight auto-save integration.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class MassConfusion(Spell):
    key = "mass_confusion"
    aliases = ["mc"]
    name = "Mass Confusion"
    school = skills.ILLUSION
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    cooldown = 0
    description = "Shatters the minds of everyone in the room — no one can tell friend from foe."
    mechanics = (
        "Unsafe AoE — applies CONFUSED to ALL entities including you!\n"
        "Confused entities attack a random target each round.\n"
        "Can hit allies, enemies, or even themselves.\n"
        "Duration: 1 round (Expert), 2 rounds (Master), 3 rounds (GM).\n"
        "Foresight charges auto-save against confusion.\n"
        "1 round cooldown."
    )

    # Duration in combat rounds per tier
    _DURATION = {
        3: 1,
        4: 2,
        5: 3,
    }

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Get all entities in room via get_room_all(caster)
        #      (includes caster — this is unsafe AoE)
        #   2. For each entity (including caster):
        #      a. Check for Foresight charges → if present, consume 1 charge,
        #         entity auto-saves, send "Your foresight warns you!" message
        #      b. If no foresight: apply CONFUSED condition
        #         - Start timer for duration_rounds
        #         - On expiry: remove CONFUSED condition
        #   3. Combat tick integration:
        #      - If attacker has CONFUSED condition, override target to random
        #        entity in room (including allies and self)
        #   4. Return multi-perspective messages
        #
        # Needs:
        #   - CONFUSED condition (added to condition.py)
        #   - Combat tick: random target override when CONFUSED
        #   - Foresight auto-save (when Foresight is implemented)
        #   - Combat-round timer for condition removal
        raise NotImplementedError(
            "Mass Confusion implementation pending — needs CONFUSED "
            "combat tick override and round-based timer."
        )

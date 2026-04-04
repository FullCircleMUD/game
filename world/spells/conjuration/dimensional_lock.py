"""
Dimensional Lock — conjuration spell, available from EXPERT mastery.

The "Fireball of conjuration" — unsafe AoE that applies DIMENSION_LOCKED
to ALL entities in the room (including caster and allies). Prevents
flee, teleport, and summon while active.

Save to escape scales with tier:
    EXPERT(3):  normal save (WIS DC),     1 round,  mana 28
    MASTER(4):  disadvantage on save,     2 rounds, mana 39
    GM(5):      no save (inescapable),    3 rounds, mana 49

Mana cost matches Fireball at each tier — you're trading damage for
total area control.

Cooldown: 1 round (default EXPERT).

DEPENDENCY: Needs DIMENSION_LOCKED condition checks in cmd_flee,
teleport spell, and any summon mechanics.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DimensionalLock(Spell):
    key = "dimensional_lock"
    aliases = ["dil"]
    name = "Dimensional Lock"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    cooldown = 0
    description = "Warps the fabric of space, locking everyone in the room in place."
    mechanics = (
        "Unsafe AoE — applies DIMENSION_LOCKED to ALL entities in room.\n"
        "Prevents flee, teleport, and summon.\n"
        "Expert: normal WIS save to resist, 1 round.\n"
        "Master: disadvantage on save, 2 rounds.\n"
        "Grandmaster: no save (inescapable), 3 rounds.\n"
        "1 round cooldown."
    )

    # (save_type, duration_rounds) per tier
    # save_type: "normal", "disadvantage", "none"
    _SCALING = {
        3: ("normal", 1),
        4: ("disadvantage", 2),
        5: ("none", 3),
    }

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Get all entities in room via get_room_all(caster) (includes caster)
        #   2. For each entity:
        #      a. If save_type != "none": roll WIS save
        #         - "normal": d20 + WIS mod vs caster's spell DC
        #         - "disadvantage": roll_with_advantage_or_disadvantage(disadvantage=True)
        #         - "none": auto-fail
        #      b. If save fails: apply DIMENSION_LOCKED condition
        #         - Start timer script for duration_rounds
        #         - On expiry: remove_condition(DIMENSION_LOCKED)
        #   3. Return messages listing who was locked and who saved
        #
        # Needs:
        #   - DIMENSION_LOCKED condition checks in cmd_flee and teleport
        #   - WIS save mechanic (WIS modifier on characters)
        #   - Spell DC calculation for caster
        #   - Combat-round-based timer for condition removal
        raise NotImplementedError(
            "Dimensional Lock implementation pending — needs DIMENSION_LOCKED "
            "condition checks in flee/teleport and WIS save mechanic."
        )

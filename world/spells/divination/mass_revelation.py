"""
Mass Revelation — divination spell, available from EXPERT mastery.

The "Fireball of divination" — strips ALL concealment from everyone
in the room. Unsafe AoE: your hidden allies lose HIDDEN too.

Removes HIDDEN and INVISIBLE conditions from all entities in the room
(excluding the caster). Does not deal damage.

Scaling:
    EXPERT(3):  removes HIDDEN + INVISIBLE,                    mana 28
    MASTER(4):  + removes GREATER_INVISIBLE,                   mana 39
    GM(5):      + reveals traps and secret exits in the room,  mana 49

Mana cost matches Fireball at each tier.

Cooldown: 1 round (default EXPERT).

DEPENDENCY: Partially implementable — HIDDEN and INVISIBLE condition
removal works now. Trap/secret exit revelation needs those systems.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class MassRevelation(Spell):
    key = "mass_revelation"
    aliases = ["mr"]
    name = "Mass Revelation"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.EXPERT
    mana_cost = {3: 28, 4: 39, 5: 49}
    target_type = "none"
    cooldown = 0
    description = "Strips all concealment from everyone in the room."
    mechanics = (
        "Unsafe AoE — removes HIDDEN and INVISIBLE from ALL entities.\n"
        "Your hidden allies will be revealed too!\n"
        "Expert: strips HIDDEN + INVISIBLE.\n"
        "Master: + strips magical invisibility (Greater Invisibility).\n"
        "Grandmaster: + reveals traps and secret exits.\n"
        "1 round cooldown."
    )

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Get all entities in room (excluding caster)
        #   2. For each entity:
        #      a. Remove HIDDEN condition if present
        #      b. Remove INVISIBLE condition if present
        #      c. At tier 4+: also handle Greater Invisibility
        #   3. At tier 5: scan room for trap objects and secret exits
        #      → reveal them in room description
        #   4. Build summary of who/what was revealed
        #   5. Return multi-perspective messages
        #
        # Needs:
        #   - HIDDEN/INVISIBLE removal (conditions exist, just call remove_condition)
        #   - Trap objects (for GM tier revelation)
        #   - Secret exit system (for GM tier)
        raise NotImplementedError(
            "Mass Revelation implementation pending — basic condition "
            "removal is ready, trap/secret exit systems needed for GM tier."
        )

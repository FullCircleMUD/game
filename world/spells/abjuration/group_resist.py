"""
Group Resist — abjuration spell, available from MASTER mastery.

Party-wide version of Resist Elements. One casting buffs the entire
group with resistance to a single damage type, making pre-fight
buffing and mid-fight rebuffing much more efficient.

Same resistance percentages as Resist Elements at equivalent tiers:
    MASTER(4): 40% resistance, mana 56  (4x individual cost of 14)
    GM(5):     60% resistance, mana 64  (4x individual cost of 16)

Duration: 30 seconds (same as individual Resist Elements).

Mana cost is 4x individual — cheaper than casting Resist Elements
on each party member individually (which would be 4-5 casts), but
still a significant mana investment.

DEPENDENCY: Needs party/group targeting system and spell parameter
support in cmd_cast (for element selection).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


# Valid elements — same as Resist Elements
_VALID_ELEMENTS = {"fire", "cold", "lightning", "acid", "poison"}


@register_spell
class GroupResist(Spell):
    key = "group_resist"
    aliases = ["gr", "gresist"]
    name = "Group Resist"
    school = skills.ABJURATION
    min_mastery = MasteryLevel.MASTER
    mana_cost = {4: 56, 5: 64}
    target_type = "none"
    description = "Grants the entire party resistance to a single damage type."
    mechanics = (
        "Usage: cast group resist <element> (fire, cold, lightning, acid, poison).\n"
        "Buffs all party members in the room with damage resistance.\n"
        "Master: 40%. Grandmaster: 60%.\n"
        "Duration: 30 seconds. Mana cost is 4x individual Resist Elements.\n"
        "2 round cooldown."
    )

    # Resistance percentage per tier (same as Resist Elements at these tiers)
    _SCALING = {
        4: 40,
        5: 60,
    }

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Parse damage type from spell parameter (same as Resist Elements)
        #   2. Get all party members in the room
        #      → needs party/group system to identify allies
        #      → fallback: all player characters in the room?
        #   3. For each party member (including caster):
        #      a. apply_resistance_effect() with the correct percentage
        #      b. Start individual timer scripts on each member
        #   4. Return success messages listing buffed party members
        #
        # Needs:
        #   - Party/group system
        #   - Spell parameter support in cmd_cast
        #   - Wall-clock timer script (30 seconds)
        raise NotImplementedError(
            "Group Resist implementation pending — needs party/group system "
            "and spell parameter support in cmd_cast."
        )

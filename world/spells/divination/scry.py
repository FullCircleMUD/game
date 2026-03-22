"""
Scry — divination spell, available from SKILLED mastery.

Remote intelligence gathering. Target a mob by name to learn information
about them without being in the same room. Information detail scales
with mastery tier.

Scaling:
    SKILLED(2): alive/dead + zone location,                    mana 15
    EXPERT(3):  + room name, current HP/max HP,                mana 25
    MASTER(4):  + full combat stats (AC, level, resistances),  mana 40
    GM(5):      + loaded items/equipment,                      mana 60

Cooldown: 30 seconds (prevent scry-spam for real-time tracking).

DEPENDENCY: Needs mob lookup by name across zones, mob stat
inspection, and equipment listing.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Scry(Spell):
    key = "scry"
    aliases = []
    name = "Scry"
    school = skills.DIVINATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 15, 3: 25, 4: 40, 5: 60}
    target_type = "none"
    cooldown = 30
    description = "Remotely gather intelligence about a creature anywhere in the world."
    mechanics = (
        "Syntax: cast scry <creature name>\n"
        "Skilled: alive/dead status + zone location.\n"
        "Expert: + room name, current HP.\n"
        "Master: + full combat stats, resistances.\n"
        "Grandmaster: + loaded items and equipment.\n"
        "30 second cooldown."
    )

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Parse spell arguments for target creature name
        #   2. Search all loaded mobs for matching name
        #      → if not found, return (False, "You sense nothing by that name.")
        #   3. Based on caster's tier, build info display:
        #      - Tier 2: "{name} is alive in {zone_name}." or "{name} is dead."
        #      - Tier 3: + "Located in: {room_name}. HP: {current}/{max}"
        #      - Tier 4: + "AC: {ac}, Level: {level}, Resists: {resistances}"
        #      - Tier 5: + "Equipment: {list of items}"
        #   4. Send info to caster only
        #   5. Return success with first-person message
        #
        # Needs:
        #   - Global mob search by name
        #   - Mob stat inspection (read-only)
        #   - Equipment listing for mobs
        raise NotImplementedError(
            "Scry implementation pending — needs global mob search "
            "and stat/equipment inspection."
        )

"""
Teleport — conjuration spell, available from SKILLED mastery.

Self-teleport to a named room. Range scales with mastery tier and is
bounded by spatial hierarchy (district < zone < world).

Scaling:
    SKILLED(2): within current district, mana 15
    EXPERT(3):  within current zone,     mana 25
    MASTER(4):  within current world,    mana 40
    GM(5):      within current world,    mana 40  (same range, cheaper effective)

Respects room flags:
    - no_teleport_out: caster cannot teleport FROM this room
    - no_teleport_to:  caster cannot teleport TO this room

Cooldown: 60 seconds (prevents teleport spam in combat/exploration).

DEPENDENCY: Needs no_teleport_to/no_teleport_out room flags on RoomBase,
world tag alongside zone/district, and room-by-name lookup.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Teleport(Spell):
    key = "teleport"
    aliases = []
    name = "Teleport"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 15, 3: 25, 4: 40, 5: 40}
    target_type = "none"
    cooldown = 60
    description = "Instantly teleport to a named location within range."
    mechanics = (
        "Self-teleport. Syntax: cast teleport <room name>\n"
        "Range: within district (Skilled), zone (Expert), world (Master/GM).\n"
        "Blocked by no_teleport_out (source) and no_teleport_to (destination).\n"
        "Blocked by DIMENSION_LOCKED condition.\n"
        "60 second cooldown."
    )

    # Range per tier: district < zone < world
    _RANGE = {
        2: "district",
        3: "zone",
        4: "world",
        5: "world",
    }

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Check caster not DIMENSION_LOCKED
        #      → if locked, return (False, "You are held in place by dimensional lock!")
        #   2. Check source room for no_teleport_out flag
        #      → if flagged, return (False, "Something prevents you from teleporting away.")
        #   3. Parse spell arguments for destination room name
        #   4. Look up destination room within range for caster's tier
        #      → district: rooms sharing same district tag
        #      → zone: rooms sharing same zone tag
        #      → world: rooms sharing same world tag
        #   5. Check destination room for no_teleport_to flag
        #      → if flagged, return (False, "Something blocks your teleport to that location.")
        #   6. Move caster to destination room
        #   7. Return success messages (departure + arrival)
        #
        # Needs:
        #   - no_teleport_to / no_teleport_out flags on RoomBase
        #   - World tag on rooms alongside zone/district
        #   - Room-by-name search within spatial scope
        raise NotImplementedError(
            "Teleport implementation pending — needs room teleport flags "
            "and spatial hierarchy (world tag)."
        )

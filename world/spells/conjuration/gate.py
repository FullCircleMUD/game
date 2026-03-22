"""
Gate — conjuration spell, available from GRANDMASTER mastery.

The trophy conjuration spell. Opens a walk-through portal to any
waygate the caster has personally discovered through exploration.
The portal persists long enough for the caster's party to walk through.

Scaling:
    GM(5): 100 mana, portal lasts 30 seconds

Waygate discovery:
    - Waygates are builder-placed objects in specific rooms
    - Characters discover waygates by visiting the room (automatic)
    - Tracked per-character: character.db.discovered_waygates = set of waygate keys
    - Being gated TO a waygate by another player does NOT count as discovery
    - You must physically visit the waygate room yourself

Cooldown: 300 seconds (5 minutes — prevent portal spam).

DEPENDENCY: Needs waygate system (builder tools, discovery tracking,
portal objects, walk-through mechanic).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class Gate(Spell):
    key = "gate"
    aliases = []
    name = "Gate"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "none"
    cooldown = 300
    description = "Opens a portal to a discovered waygate that your party can walk through."
    mechanics = (
        "Opens a walk-through portal to any waygate you have discovered.\n"
        "Syntax: cast gate <waygate name>\n"
        "Portal lasts 30 seconds — party members can walk through.\n"
        "You must have personally visited the waygate to gate to it.\n"
        "Being gated there by another player does NOT count as discovery.\n"
        "100 mana. 5 minute cooldown."
    )

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Check caster not DIMENSION_LOCKED
        #   2. Parse spell arguments for waygate name
        #   3. Look up waygate in caster's discovered_waygates set
        #      → if not discovered, return (False, "You haven't discovered that waygate.")
        #   4. Look up waygate room object
        #   5. Spawn portal object in caster's room
        #      - Portal has "enter" command that moves user to waygate room
        #      - Portal disappears after 30 seconds (timer script)
        #   6. Return success messages
        #
        # Needs:
        #   - Waygate objects (builder-placed, auto-discovery on room entry)
        #   - character.db.discovered_waygates tracking
        #   - Portal object typeclass with enter command
        #   - Timer script for portal despawn
        raise NotImplementedError(
            "Gate implementation pending — needs waygate system "
            "(discovery tracking, portal objects)."
        )

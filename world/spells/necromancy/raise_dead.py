"""
Raise Dead — necromancy spell, available from SKILLED mastery.

Raises corpses in the room as undead minions that fight for the caster.
Scales in both number of corpses raised AND duration before the undead
disintegrate.

Scaling:
    SKILLED(2): 1 corpse, 2 minutes duration,  mana 15
    EXPERT(3):  2 corpses, 5 minutes duration,  mana 25
    MASTER(4):  3 corpses, 10 minutes duration, mana 40
    GM(5):      4 corpses, 30 minutes duration,  mana 60

Corpse protection rules:
    - Character (player) corpses that still have equipment on them
      CANNOT be raised — this protects dead players' gear recovery
    - Once a player corpse has been looted (no equipment remaining),
      it becomes fair game for raising
    - NPC/mob corpses can always be raised regardless of equipment

The raised minion's power is based on the original creature. A goblin
corpse becomes a goblin skeleton; a dragon corpse becomes a dragon
zombie. Higher tier doesn't make individual minions stronger — it
lets you raise MORE of them for LONGER.

When the duration expires, the undead crumbles to dust and disappears.

Cooldown: 0 (limited by corpse availability).

DEPENDENCY: Needs pet/retainer system, corpse objects from mob death
system, and NPC AI for minion combat behavior.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class RaiseDead(Spell):
    key = "raise_dead"
    aliases = ["rd", "raise"]
    name = "Raise Dead"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.SKILLED
    mana_cost = {2: 15, 3: 25, 4: 40, 5: 60}
    target_type = "none"
    cooldown = 0
    description = "Raises corpses as undead minions that fight for you."
    mechanics = (
        "Requires corpses in the room. Consumes corpses on success.\n"
        "Player corpses with equipment CANNOT be raised (protects gear recovery).\n"
        "Looted player corpses and all NPC corpses are fair game.\n"
        "Corpses raised / duration: 1/2min (Skilled), 2/5min (Expert),\n"
        "  3/10min (Master), 4/30min (Grandmaster).\n"
        "Minion power based on original creature.\n"
        "When duration expires, the undead crumbles to dust.\n"
        "No cooldown — limited by corpse availability."
    )

    # (max corpses, duration in minutes) per tier
    _SCALING = {
        2: (1, 2),
        3: (2, 5),
        4: (3, 10),
        5: (4, 30),
    }

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Search room for corpse objects
        #      → if none found, return (False, "There are no corpses here to raise.")
        #   2. Filter out protected corpses:
        #      → Player corpses WITH equipment still on them: skip
        #      → Player corpses that have been looted (empty): allow
        #      → NPC/mob corpses: always allow
        #   3. Determine how many to raise: min(available_corpses, max_from_scaling)
        #   4. For each corpse raised:
        #      a. Consume the corpse (delete corpse object)
        #      b. Spawn undead NPC based on original creature
        #      c. Set minion's owner to caster
        #      d. Start timer script for duration — on expiry, minion crumbles
        #   5. Minions join combat on caster's side if in combat
        #   6. Return success messages listing what was raised
        #
        # Needs:
        #   - Pet/retainer system (NPC ownership, commands, AI)
        #   - Corpse objects (created when mobs/players die)
        #   - Corpse equipment check (has_equipment property)
        #   - Undead NPC spawning from corpse template
        #   - Wall-clock timer for minion duration
        raise NotImplementedError(
            "Raise Dead implementation pending — needs pet/retainer system "
            "and corpse objects from mob death system."
        )

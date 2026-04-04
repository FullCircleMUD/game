"""
Death Mark — necromancy spell, available from GRANDMASTER mastery.

The GM capstone for necromancy. Marks a single target with a skull-shaped
sigil. For 1 combat round, ALL damage dealt to the marked target by
ANYONE (weapons, spells, everything) heals the attacker for the damage
amount.

The mirror of Power Word: Death — PWD says "you die instantly", Death
Mark says "your death feeds us all."

Mechanic:
    - Applies DEATH_MARKED condition to target for 1 combat round
    - While marked: all damage sources heal the attacker for damage dealt
    - Includes spell damage, weapon damage, everything
    - Heal is capped at each attacker's max HP (no over-heal)
    - The mark does NOT deal any damage itself — it's purely a debuff
    - Target can still act normally (they just feed their attackers)

Tactical use:
    - Necro marks boss → yells "HIT THEM NOW!" → party bursts
    - Coordinate with evoker's Fireball: everyone in the blast zone
      who damages the marked target heals (AoE still hurts your party
      normally for non-marked targets)
    - Time with warrior's strongest attacks for maximum drain
    - In PvP: mark and focus-fire, entire team heals

Cost: 100 mana (matches PWD and Invulnerability)
Cooldown: 3 rounds (default GM cooldown)

DEPENDENCY: Needs damage pipeline hook to check for DEATH_MARKED on
target and heal attacker, plus combat round timer.
"""

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class DeathMark(Spell):
    key = "death_mark"
    aliases = ["dm"]
    name = "Death Mark"
    school = skills.NECROMANCY
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "hostile"
    description = "Brands the target with a death mark — all damage heals the attacker."
    mechanics = (
        "Marks a single target for 1 combat round.\n"
        "ALL damage dealt to the marked target heals the attacker.\n"
        "Includes weapon damage, spell damage, everything.\n"
        "Heal capped at each attacker's max HP.\n"
        "The mark itself deals no damage — it's a debuff.\n"
        "100 mana. 3 round cooldown."
    )

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Check if target already has DEATH_MARKED condition
        #      → if yes, return (False, "Target is already death marked.")
        #   2. Apply DEATH_MARKED condition to target
        #   3. Start DeathMarkTimerScript on target:
        #      - 1 combat round duration
        #      - On expiry: remove DEATH_MARKED condition
        #   4. Damage pipeline integration:
        #      - In apply_spell_damage() and combat damage resolution:
        #        if target has DEATH_MARKED, heal attacker for damage dealt
        #        (capped at attacker's max HP)
        #   5. Return success messages
        #
        # Needs:
        #   - Combat round timer script
        #   - Damage pipeline hook (check DEATH_MARKED on target)
        #   - Integration with both spell damage AND weapon damage paths
        raise NotImplementedError(
            "Death Mark implementation pending — needs damage pipeline hook "
            "to heal attackers and combat round timer."
        )

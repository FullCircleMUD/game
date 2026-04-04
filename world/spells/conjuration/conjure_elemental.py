"""
Conjure Elemental — conjuration spell, available from MASTER mastery.

Summons a powerful elemental combat pet that fights alongside the caster.
The elemental's type and power scale with the caster's tier.

Scaling:
    MASTER(4):  Lesser elemental (fire/ice/earth/air), 10 minutes, mana 56
    GM(5):      Greater elemental, 30 minutes,                    mana 64

Only one conjured elemental at a time. Recasting replaces the current one.

Cooldown: 0 (limited by duration and single-summon cap).

DEPENDENCY: Needs pet/retainer system, elemental NPC prototypes,
and NPC AI for combat behavior.
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class ConjureElemental(Spell):
    key = "conjure_elemental"
    aliases = ["ce"]
    name = "Conjure Elemental"
    school = skills.CONJURATION
    min_mastery = MasteryLevel.MASTER
    mana_cost = {4: 56, 5: 64}
    target_type = "none"
    cooldown = 0
    description = "Summons a powerful elemental to fight at your side."
    mechanics = (
        "Summons an elemental combat pet. One active at a time.\n"
        "Master: lesser elemental, 10 minutes.\n"
        "Grandmaster: greater elemental, 30 minutes.\n"
        "Elemental type chosen on cast: fire, ice, earth, or air.\n"
        "Recasting dismisses the current elemental before summoning a new one.\n"
        "Blocked by DIMENSION_LOCKED condition."
    )

    # (elemental_tier, duration_minutes) per tier
    _SCALING = {
        4: ("lesser", 10),
        5: ("greater", 30),
    }

    def _execute(self, caster, target):
        # SCAFFOLD: Implementation pending.
        #
        # When implemented:
        #   1. Check caster not DIMENSION_LOCKED
        #   2. If caster already has a conjured elemental, dismiss it
        #   3. Parse spell arguments for elemental type (fire/ice/earth/air)
        #   4. Spawn elemental NPC from prototype
        #   5. Set elemental's owner to caster
        #   6. Start timer for duration — on expiry, elemental despawns
        #   7. Elemental joins combat on caster's side if in combat
        #   8. Return success messages
        #
        # Needs:
        #   - Pet/retainer system (ownership, commands, AI)
        #   - Elemental NPC prototypes (fire/ice/earth/air, lesser/greater)
        #   - DIMENSION_LOCKED check (blocks summoning)
        raise NotImplementedError(
            "Conjure Elemental implementation pending — needs pet/retainer "
            "system and elemental NPC prototypes."
        )

"""
Word of God — divine dominion spell, available from GRANDMASTER mastery.

Mass stun all enemies in the room. No save on the first round —
subsequent rounds allow contested WIS saves to break free.

Scaling:
    GM(5): mana 100

Cooldown: 3 rounds (default GM).
"""

from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from world.spells.base_spell import Spell
from world.spells.registry import register_spell


@register_spell
class WordOfGod(Spell):
    key = "word_of_god"
    aliases = ["wog"]
    name = "Word of God"
    school = skills.DIVINE_DOMINION
    min_mastery = MasteryLevel.GRANDMASTER
    mana_cost = {5: 100}
    target_type = "none"
    description = "Speaks a word of divine authority that stuns all enemies in the room."
    mechanics = (
        "Unsafe AoE — stuns all enemies in room.\n"
        "No save on first round. Contested WIS save each subsequent round.\n"
        "3 round cooldown."
    )

    def _execute(self, caster, target):
        raise NotImplementedError(
            "Word of God implementation pending — needs mass STUNNED "
            "condition application with no-save first round and "
            "per-round contested WIS saves after."
        )

"""
DeathCause enum — cause-of-death for corpse descriptions.

Each value maps to a flavour description template used by the Corpse typeclass.
"""

from enum import Enum


class DeathCause(Enum):
    STARVATION = "starvation"
    DROWNING = "drowning"
    COMBAT = "combat"
    FALL = "fall"
    POISON = "poison"
    DEFEAT = "defeat"
    UNKNOWN = "unknown"

    def corpse_desc(self, name):
        """Return the room description for a corpse with this cause of death."""
        return _CORPSE_DESCRIPTIONS[self].format(name=name)


_CORPSE_DESCRIPTIONS = {
    DeathCause.STARVATION: "The emaciated corpse of {name} lies here.",
    DeathCause.DROWNING: "The waterlogged corpse of {name} floats here.",
    DeathCause.COMBAT: "The beaten and bloody corpse of {name} lies here.",
    DeathCause.FALL: "The broken corpse of {name} lies here.",
    DeathCause.POISON: "The discoloured corpse of {name} lies here.",
    DeathCause.DEFEAT: "The fallen form of {name} was dragged from the arena.",
    DeathCause.UNKNOWN: "The corpse of {name} lies here.",
}

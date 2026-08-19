"""
AggressiveMob — convenience class composing AggressiveMixin + CombatMob.

Used as a concrete typeclass by fcm-mobs spawn rules (e.g. the sewer
rats in shard0/millholm/sewers.yaml) and as a base class for concrete
aggressive mob subclasses (Wolf, Kobold, Gnoll, etc.).

Aggression logic lives in AggressiveMixin; this class is pure composition.
"""

from typeclasses.actors.mob import CombatMob
from typeclasses.mixins.aggressive_mixin import AggressiveMixin


class AggressiveMob(AggressiveMixin, CombatMob):
    """CombatMob with aggression behavior — attacks players on sight."""

    pass

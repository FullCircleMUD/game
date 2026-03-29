"""
BaseMarineMob — passive aquatic mob base class.

Composes SwimmingMixin (Condition.WATER_BREATHING, preferred_depth,
dive/surface) with CombatMob. Spawns underwater at preferred_depth.
Not aggressive by default — no AggressiveMixin.

For aggressive marine mobs (sharks, eels), compose AggressiveMixin
separately:
    class Shark(AggressiveMixin, BaseMarineMob):
        ...

Usage:
    Spawn via JSON attrs on BaseMarineMob, or subclass for
    specific marine creatures with custom AI.
"""

from typeclasses.actors.mob import CombatMob
from typeclasses.mixins.swimming_mixin import SwimmingMixin


class BaseMarineMob(SwimmingMixin, CombatMob):
    """Passive aquatic mob. Spawns underwater, flees from threats."""

    pass

"""
Skeleton — basic undead aggressive mob.

Tags itself as creature_type=undead at creation for Turn Undead
and similar ability checks. Stats set via spawn JSON attrs.
"""

from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class Skeleton(HumanoidWearslotsMixin, AggressiveMob):
    """An undead skeleton. Tagged for Turn Undead."""

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("undead", category="creature_type")

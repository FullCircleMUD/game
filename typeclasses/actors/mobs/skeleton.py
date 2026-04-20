"""
Skeleton — basic undead aggressive mob.

Tags itself as creature_type=undead at creation for Turn Undead
and similar ability checks. Stats set via spawn JSON attrs.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from typeclasses.actors.mobs.aggressive_mob import AggressiveMob
from typeclasses.mixins.wearslots.humanoid_wearslots import HumanoidWearslotsMixin


class Skeleton(HumanoidWearslotsMixin, AggressiveMob):
    """An undead skeleton. Tagged for Turn Undead."""

    alignment_score = AttributeProperty(-1000)  # pure evil undead
    damage_type = AttributeProperty(DamageType.SLASHING)  # claws
    room_description = AttributeProperty(
        "clacks its yellowed teeth, empty eye sockets turning to follow any movement."
    )

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("undead", category="creature_type")

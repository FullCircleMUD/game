"""
FamiliarHawk — MASTER tier familiar. Flies and fights.

Composes FlyingMixin + CombatCompanionMixin — can scout aerially
and also join combat alongside the caster.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.damage_type import DamageType
from enums.size import Size
from typeclasses.actors.pets.base_pet import BasePet
from typeclasses.mixins.combat_companion import CombatCompanionMixin
from typeclasses.mixins.familiar_mixin import FamiliarMixin
from typeclasses.mixins.flying_mixin import FlyingMixin


class FamiliarHawk(FamiliarMixin, FlyingMixin, CombatCompanionMixin, BasePet):
    """A combat-capable hawk familiar — MASTER conjuration."""

    pet_type = AttributeProperty("familiar")
    base_size = AttributeProperty(Size.TINY.value)
    size = AttributeProperty(Size.TINY.value)
    preferred_height = AttributeProperty(0)
    room_description = AttributeProperty("circles watchfully above its master.")

    damage_dice = "1d4"
    damage_type = DamageType.SLASHING
    attack_message = "dives and rakes at"
    attack_delay_min = 3
    attack_delay_max = 5
    initiative_speed = 3

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A fierce hawk with sharp golden eyes and wickedly curved "
            "talons. Arcane sigils shimmer faintly along the edges of "
            "its wing feathers."
        )
        self.hp_max = 12
        self.hp = 12
        self.level = 3
        self.strength = 10
        self.dexterity = 16

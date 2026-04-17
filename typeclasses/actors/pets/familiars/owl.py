"""
FamiliarOwl — EXPERT tier familiar. Can fly — aerial scouting.

Composes FlyingMixin for vertical movement (ascend/descend), allowing
the caster to scout rooms at different heights via remote control.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.pets.base_pet import BasePet
from typeclasses.mixins.familiar_mixin import FamiliarMixin
from typeclasses.mixins.flying_mixin import FlyingMixin


class FamiliarOwl(FamiliarMixin, FlyingMixin, BasePet):
    """A flying owl familiar — EXPERT conjuration."""

    pet_type = AttributeProperty("familiar")
    size = AttributeProperty("small")
    preferred_height = AttributeProperty(0)  # starts on ground with owner
    room_description = AttributeProperty("perches on its master's shoulder.")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A tawny owl with enormous amber eyes that seem to glow "
            "faintly with arcane energy. Its head swivels silently, "
            "taking in every detail of its surroundings."
        )
        self.hp_max = 8
        self.hp = 8
        self.level = 2

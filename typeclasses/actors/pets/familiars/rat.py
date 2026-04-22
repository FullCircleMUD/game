"""
FamiliarRat — BASIC tier familiar. Small, goes anywhere.

No special abilities beyond the core FamiliarMixin remote control.
The entry-level scout.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.pets.base_pet import BasePet
from typeclasses.mixins.familiar_mixin import FamiliarMixin


class FamiliarRat(FamiliarMixin, BasePet):
    """A small rat familiar — BASIC conjuration."""

    pet_type = AttributeProperty("familiar")
    species = AttributeProperty("rat")
    base_size = AttributeProperty(Size.TINY.value)
    size = AttributeProperty(Size.TINY.value)
    room_description = AttributeProperty("scurries along at its master's heels.")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A small grey rat with bright, intelligent eyes. It watches "
            "everything with an alertness that seems almost unnatural "
            "for a rodent."
        )
        self.hp_max = 4
        self.hp = 4
        self.level = 1

"""
FamiliarCat — SKILLED tier familiar. Stealth — doesn't trigger mob aggro.

Overrides at_new_arrival handling so aggressive mobs ignore it, making
it ideal for scouting dangerous areas safely.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.pets.base_pet import BasePet
from typeclasses.mixins.familiar_mixin import FamiliarMixin


class FamiliarCat(FamiliarMixin, BasePet):
    """A stealthy cat familiar — SKILLED conjuration."""

    pet_type = AttributeProperty("familiar")
    species = AttributeProperty("cat")
    base_size = AttributeProperty(Size.TINY.value)
    size = AttributeProperty(Size.TINY.value)
    room_description = AttributeProperty("pads silently alongside its master.")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A sleek black cat with luminous green eyes. It moves with "
            "preternatural silence, barely disturbing the air as it passes."
        )
        self.hp_max = 6
        self.hp = 6
        self.level = 1

    def at_new_arrival(self, arriving_obj):
        """Override — cat does not trigger mob aggro when it arrives."""
        pass

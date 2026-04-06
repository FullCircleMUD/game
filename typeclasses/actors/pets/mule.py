"""
Mule — medium-sized pack animal pet.

The mule is the first POC pet. Medium-sized so it can go anywhere
(including indoors), useful for carrying capacity (future: panniers),
not a fighter.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.pets.base_pet import BasePet


class Mule(BasePet):
    """A sturdy mule. Medium-sized pack animal."""

    pet_type = AttributeProperty("mule")
    size = AttributeProperty("medium")

    # ── Stats — hardy but not a fighter ──
    level = AttributeProperty(1)
    hp = AttributeProperty(20)
    base_hp_max = AttributeProperty(20)
    hp_max = AttributeProperty(20)
    base_strength = AttributeProperty(14)
    strength = AttributeProperty(14)
    base_constitution = AttributeProperty(14)
    constitution = AttributeProperty(14)

    # ── Display ──
    room_description = AttributeProperty("stands here, flicking its ears.")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A sturdy brown mule with a thick neck and patient eyes. "
            "Its hooves are worn from travel and its coat is dusty "
            "from the road."
        )

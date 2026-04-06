"""
WarDog — medium-sized combat companion pet.

A trained war dog that fights alongside its owner. Bites enemies,
medium-sized (goes anywhere), decent HP for a pet.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.pets.base_pet import BasePet
from typeclasses.mixins.combat_companion import CombatCompanionMixin


class WarDog(CombatCompanionMixin, BasePet):
    """A trained war dog. Medium-sized combat companion."""

    size = AttributeProperty("medium")

    # ── Combat ──
    damage_dice = AttributeProperty("1d6")
    attack_message = AttributeProperty("bites at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(4)
    initiative_speed = AttributeProperty(2)  # fairly quick

    # ── Stats ──
    level = AttributeProperty(2)
    hp = AttributeProperty(25)
    base_hp_max = AttributeProperty(25)
    hp_max = AttributeProperty(25)
    base_strength = AttributeProperty(12)
    strength = AttributeProperty(12)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(12)
    constitution = AttributeProperty(12)

    # ── Display ──
    room_description = AttributeProperty("stands guard here, hackles raised.")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A muscular dog with a broad chest and powerful jaws. "
            "Its eyes are alert and watchful, trained to protect "
            "its master. Scars on its muzzle speak of past battles."
        )

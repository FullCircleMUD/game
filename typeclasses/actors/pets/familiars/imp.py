"""
FamiliarImp — GM tier familiar. Flies, fights, and illuminates.

The ultimate familiar — composes FlyingMixin + CombatCompanionMixin
and applies LIGHT_SPELL effect, illuminating any dark room it enters.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.pets.base_pet import BasePet
from typeclasses.mixins.combat_companion import CombatCompanionMixin
from typeclasses.mixins.familiar_mixin import FamiliarMixin
from typeclasses.mixins.flying_mixin import FlyingMixin


class FamiliarImp(FamiliarMixin, FlyingMixin, CombatCompanionMixin, BasePet):
    """A combat-capable, light-bearing imp familiar — GM conjuration."""

    pet_type = AttributeProperty("familiar")
    base_size = AttributeProperty(Size.SMALL.value)
    size = AttributeProperty(Size.SMALL.value)
    preferred_height = AttributeProperty(0)
    room_description = AttributeProperty("hovers at its master's side, flickering with arcane light.")

    damage_dice = "1d6"
    attack_message = "hurls a spark of fire at"
    attack_delay_min = 3
    attack_delay_max = 4
    initiative_speed = 3

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A small, bat-winged creature with mottled red skin and "
            "mischievous yellow eyes. Flickering arcane flames dance "
            "along its fingertips, casting a warm glow that illuminates "
            "everything nearby."
        )
        self.hp_max = 16
        self.hp = 16
        self.level = 4
        self.strength = 10
        self.dexterity = 16
        self.intelligence = 14

        # Permanent LIGHT_SPELL effect — illuminates rooms
        from enums.named_effect import NamedEffect
        self.apply_named_effect(
            NamedEffect.LIGHT_SPELL,
            duration=None,  # permanent
            duration_type=None,  # no timer
        )

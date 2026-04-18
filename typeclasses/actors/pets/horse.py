"""
Horse — large-sized mount.

First mount POC. Large-sized (can't enter indoor rooms while mounted),
300 move stamina pool, can kick in combat.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.size import Size
from typeclasses.actors.pets.base_pet import BasePet
from typeclasses.mixins.combat_companion import CombatCompanionMixin
from typeclasses.mixins.mount_mixin import MountMixin


class Horse(CombatCompanionMixin, MountMixin, BasePet):
    """A riding horse. Large mount with combat kick."""

    pet_type = AttributeProperty("horse")
    base_size = AttributeProperty(Size.LARGE.value)
    size = AttributeProperty(Size.LARGE.value)
    # ── Movement ──
    move = AttributeProperty(300)
    base_move_max = AttributeProperty(300)
    move_max = AttributeProperty(300)

    # ── Combat ──
    damage_dice = AttributeProperty("1d4")
    attack_message = AttributeProperty("kicks at")
    attack_delay_min = AttributeProperty(4)
    attack_delay_max = AttributeProperty(6)
    initiative_speed = AttributeProperty(2)

    # ── Stats ──
    level = AttributeProperty(2)
    hp = AttributeProperty(30)
    base_hp_max = AttributeProperty(30)
    hp_max = AttributeProperty(30)
    base_strength = AttributeProperty(16)
    strength = AttributeProperty(16)
    base_constitution = AttributeProperty(14)
    constitution = AttributeProperty(14)

    # ── Display ──
    room_description = AttributeProperty("stands here, pawing the ground.")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = (
            "A strong brown horse with a glossy coat and alert ears. "
            "It stamps impatiently, ready to run."
        )

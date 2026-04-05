"""
Owl (bird) — non-aggressive flying mob at Owl's House in the Hundred Acre Wood.

Spawns at height 1 (up in the tree). Invisible from ground level —
players only see them when they fly up. Non-aggressive, just
atmospheric. Weak — not intended as a real fight.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.actors.mob import CombatMob
from typeclasses.mixins.flying_mixin import FlyingMixin


class OwlBird(FlyingMixin, CombatMob):
    """An owl perched in the branches. Non-aggressive."""

    size = AttributeProperty("small")
    room_description = AttributeProperty("perches in the branches, watching with large round eyes.")

    # ── Flight ──
    preferred_height = AttributeProperty(1)

    # ── Stats ──
    hp = AttributeProperty(15)
    base_hp_max = AttributeProperty(15)
    hp_max = AttributeProperty(15)
    base_strength = AttributeProperty(4)
    strength = AttributeProperty(4)
    base_dexterity = AttributeProperty(14)
    dexterity = AttributeProperty(14)
    base_constitution = AttributeProperty(4)
    constitution = AttributeProperty(4)
    base_armor_class = AttributeProperty(13)
    armor_class = AttributeProperty(13)
    level = AttributeProperty(1)

    # ── Combat ──
    initiative_speed = AttributeProperty(3)
    damage_dice = AttributeProperty("1d2")
    attack_message = AttributeProperty("pecks at")
    attack_delay_min = AttributeProperty(3)
    attack_delay_max = AttributeProperty(6)

    # ── Behavior ──
    aggro_hp_threshold = AttributeProperty(0.5)
    max_per_room = AttributeProperty(0)

    # ── AI timing ──
    ai_tick_interval = AttributeProperty(10)
    respawn_delay = AttributeProperty(120)

    def ai_wander(self):
        """Stay in the tree — owls don't wander."""
        if (
            self.location
            and not self.scripts.get("combat_handler")
            and self.room_vertical_position < self.preferred_height
        ):
            self.ascend(self.preferred_height - self.room_vertical_position)

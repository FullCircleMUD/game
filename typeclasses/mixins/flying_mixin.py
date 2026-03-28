"""
FlyingMixin — innate flight for mobs and NPCs.

Grants the FLY condition at creation so existing height-aware systems
(can_reach_target, _try_match_height) work without modification.
Sets room_vertical_position to preferred_height on spawn.

Usage:
    class Crow(FlyingMixin, AggressiveMob):
        preferred_height = AttributeProperty(1)
"""

from evennia.typeclasses.attributes import AttributeProperty


class FlyingMixin:
    """Mixin providing innate flight for mobs/NPCs."""

    can_fly = True
    preferred_height = AttributeProperty(1)

    def at_object_creation(self):
        super().at_object_creation()
        from enums.condition import Condition
        self.add_condition(Condition.FLY)
        self.room_vertical_position = self.preferred_height

    def ascend(self, levels=1):
        """Move up by levels. Capped by room max_height."""
        room = self.location
        max_h = getattr(room, "max_height", 1) if room else 1
        new_pos = min(self.room_vertical_position + levels, max_h)
        if new_pos != self.room_vertical_position:
            self.room_vertical_position = new_pos
            return True
        return False

    def descend(self, levels=1):
        """Move down by levels. Won't go below 0 (ground)."""
        new_pos = max(0, self.room_vertical_position - levels)
        if new_pos != self.room_vertical_position:
            self.room_vertical_position = new_pos
            return True
        return False

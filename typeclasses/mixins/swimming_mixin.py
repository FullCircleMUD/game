"""
SwimmingMixin — innate aquatic movement for mobs and NPCs.

Grants the WATER_BREATHING condition at creation so existing height-aware
systems (_try_match_height) work for underwater targets without modification.
Sets room_vertical_position to preferred_depth on spawn.

Usage:
    class Shark(SwimmingMixin, AggressiveMob):
        preferred_depth = AttributeProperty(-1)
"""

from evennia.typeclasses.attributes import AttributeProperty


class SwimmingMixin:
    """Mixin providing innate aquatic movement for mobs/NPCs."""

    can_swim = True
    preferred_depth = AttributeProperty(-1)

    def at_object_creation(self):
        super().at_object_creation()
        from enums.condition import Condition
        self.add_condition(Condition.WATER_BREATHING)
        self.room_vertical_position = self.preferred_depth

    def dive(self, levels=1):
        """Move deeper by levels. Capped by room max_depth."""
        room = self.location
        max_d = getattr(room, "max_depth", 0) if room else 0
        new_pos = max(self.room_vertical_position - levels, max_d)
        if new_pos != self.room_vertical_position:
            self.room_vertical_position = new_pos
            return True
        return False

    def surface(self, levels=1):
        """Move toward surface by levels. Won't go above 0 (surface)."""
        new_pos = min(0, self.room_vertical_position + levels)
        if new_pos != self.room_vertical_position:
            self.room_vertical_position = new_pos
            return True
        return False

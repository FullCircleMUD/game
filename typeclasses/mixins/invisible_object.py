"""
InvisibleObjectMixin — adds invisible state to world objects.

Invisible objects can only be seen by characters with the DETECT_INVIS
condition. This is the same gate used for invisible characters, but
applied to objects via a simple boolean attribute rather than a
reference-counted condition.

Usage:
    class WorldChest(InvisibleObjectMixin, WorldFixture):
        def at_object_creation(self):
            super().at_object_creation()
            self.at_invisible_init()
"""

from evennia.typeclasses.attributes import AttributeProperty


class InvisibleObjectMixin:
    """
    Mixin that tracks invisible state for world objects.

    Child classes MUST:
        1. Call at_invisible_init() from at_object_creation()
    """

    is_invisible = AttributeProperty(False)

    def at_invisible_init(self):
        """
        Initialize invisible object state. Call from at_object_creation().
        Safe to call multiple times.
        """
        pass  # default set via AttributeProperty

    def is_invis_visible_to(self, character):
        """
        Check invisible-state visibility for a character.

        Visible if:
            - Not invisible, OR
            - Character has DETECT_INVIS condition
        """
        if not self.is_invisible:
            return True

        from enums.condition import Condition

        if hasattr(character, "has_condition"):
            return character.has_condition(Condition.DETECT_INVIS)

        return False
